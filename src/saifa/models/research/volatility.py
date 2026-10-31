"""Past-only annual GARCH fits with daily variance updates and EWMA dependence."""

from dataclasses import asdict

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from saifa.domain.config import BacktestConfig, OptimisationConfig
from saifa.domain.dashboard import CONFIDENCES
from saifa.domain.research import GarchFit, ResearchConfig
from saifa.models.risk import empirical_tail, normal_tail
from saifa.models.walk_forward import forecast_positions


def variance_path(
    residuals: np.ndarray, omega: float, alpha: float, beta: float, initial: float
) -> np.ndarray:
    if (
        not np.isfinite([omega, alpha, beta, initial]).all()
        or omega <= 0
        or min(alpha, beta) < 0
        or alpha + beta >= 1
        or initial <= 0
    ):
        raise ValueError("Invalid stationary GARCH parameters")
    residuals = np.asarray(residuals, dtype=float)
    if residuals.ndim != 1 or not len(residuals) or not np.isfinite(residuals).all():
        raise ValueError("Finite nonempty residual sequence required")
    values = np.empty(len(residuals))
    values[0] = initial
    for i in range(1, len(values)):
        values[i] = omega + alpha * residuals[i - 1] ** 2 + beta * values[i - 1]
    return values


def fit_garch(returns: np.ndarray) -> GarchFit:
    """Gaussian variance QMLE conditional on a sample-mean estimate, in percent units."""
    values = np.asarray(returns, dtype=float) * 100
    if values.ndim != 1 or len(values) < 252 or not np.isfinite(values).all():
        raise ValueError("GARCH requires at least 252 finite return observations")
    mean = float(values.mean())
    residuals = values - mean
    initial = float(np.var(residuals))
    if initial < 1e-10:
        raise ValueError("GARCH is not estimable on a constant return series")

    def objective(theta):
        if theta[1] + theta[2] >= 0.999:
            return 1e20
        h = variance_path(residuals, *theta, initial)
        return float(0.5 * np.sum(np.log(h) + residuals**2 / h))

    fits = [
        minimize(
            objective,
            [initial * (1 - a - b), a, b],
            method="SLSQP",
            bounds=[(1e-8, initial * 100), (0, 0.998), (0, 0.998)],
            constraints=[{"type": "ineq", "fun": lambda p: 0.998999 - p[1] - p[2]}],
            options={"ftol": 1e-8, "maxiter": 500},
        )
        for a, b in ((0.05, 0.9), (0.1, 0.8))
    ]
    fits = [f for f in fits if f.success and np.isfinite(f.fun)]
    if not fits:
        raise RuntimeError("GARCH variance optimisation did not converge")
    best = min(fits, key=lambda f: f.fun)
    omega, alpha, beta = map(float, best.x)
    h = variance_path(residuals, omega, alpha, beta, initial)
    next_variance = (omega + alpha * residuals[-1] ** 2 + beta * h[-1]) / 10000
    return GarchFit(
        mean / 100,
        omega / 10000,
        alpha,
        beta,
        next_variance,
        tuple(residuals / np.sqrt(h)),
        str(best.message),
    )


def volatility_experiment(
    returns: pd.DataFrame,
    portfolios: pd.DataFrame,
    policy: OptimisationConfig,
    settings: ResearchConfig,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    config = BacktestConfig(
        start=policy.development_end_exclusive,
        end_exclusive=policy.evaluation_end_exclusive,
        lookback_observations=settings.volatility_lookback,
        confidence_levels=CONFIDENCES,
        reference_nav=policy.initial_capital,
    )
    positions = forecast_positions(returns, config)
    values = returns.to_numpy(dtype=float)
    weights = {
        s: portfolios.loc[s].reindex(returns.columns).to_numpy(dtype=float)
        for s in portfolios.index
    }
    projected = {s: values @ w for s, w in weights.items()}
    dev = returns.index < policy.development_end_exclusive
    regime_levels = {
        s: float(pd.Series(r[dev]).rolling(21).std().median()) for s, r in projected.items()
    }
    rows, fits, correlations = [], [], []
    year = None
    models, variances = {}, {}
    for pos in positions:
        date, as_of = returns.index[pos], returns.index[pos - 1]
        first = pos - settings.volatility_lookback
        if date.year != year:
            year = date.year
            history = values[first:pos]
            mean_vector = history.mean(axis=0)
            covariance = np.cov(history, rowvar=False, ddof=1)
            models, variances = {}, {}
            fit_start, fit_end = returns.index[first], as_of
            for strategy, series in projected.items():
                record = {
                    "strategy": strategy,
                    "execution_year": year,
                    "training_start": str(returns.index[first].date()),
                    "training_end": str(as_of.date()),
                }
                try:
                    fit = fit_garch(series[first:pos])
                    models[strategy] = fit
                    variances[strategy] = fit.next_variance
                    fits.append(
                        {
                            **record,
                            **{
                                k: v
                                for k, v in asdict(fit).items()
                                if k != "standardized_residuals"
                            },
                            "status": "ok",
                        }
                    )
                except (ValueError, RuntimeError) as exc:
                    fits.append({**record, "status": "unavailable", "message": str(exc)})
        sd = np.sqrt(np.diag(covariance))
        for i in range(len(sd)):
            for j in range(i + 1, len(sd)):
                correlations.append(
                    {
                        "forecast_date": str(date.date()),
                        "as_of": str(as_of.date()),
                        "asset_1": returns.columns[i],
                        "asset_2": returns.columns[j],
                        "correlation": covariance[i, j] / sd[i] / sd[j]
                        if sd[i] * sd[j] > 0
                        else np.nan,
                    }
                )
        for strategy, series in projected.items():
            fit = models.get(strategy)
            daily_vol = float(np.sqrt(variances[strategy])) if fit else np.nan
            ewma_mean = float(weights[strategy] @ mean_vector)
            ewma_vol = float(np.sqrt(max(0, weights[strategy] @ covariance @ weights[strategy])))
            past_vol = float(np.std(series[pos - 21 : pos], ddof=1))
            regime = (
                "high prior volatility"
                if past_vol > regime_levels[strategy]
                else "low prior volatility"
            )
            for confidence in CONFIDENCES:
                estimates = [
                    (
                        "ewma_normal",
                        normal_tail(ewma_mean, ewma_vol, confidence),
                        "EWMA covariance with Gaussian tails; not DCC or a copula model",
                        ewma_vol,
                    )
                ]
                if fit:
                    standardized = empirical_tail(-np.array(fit.standardized_residuals), confidence)
                    from saifa.domain.risk import TailEstimate

                    fhs = TailEstimate(
                        -fit.mean + daily_vol * standardized.var_fraction,
                        -fit.mean + daily_vol * standardized.es_fraction,
                    )
                    estimates += [
                        (
                            "garch_normal",
                            normal_tail(fit.mean, daily_vol, confidence),
                            "Gaussian GARCH; conditional variance uncertainty excluded",
                            daily_vol,
                        ),
                        (
                            "garch_fhs",
                            fhs,
                            f"Training standardized residual empirical tail: {len(fit.standardized_residuals) * (1 - confidence):g} effective tail observations; extremes remain sample-sensitive",
                            daily_vol,
                        ),
                    ]
                else:
                    estimates += [
                        (m, None, "Annual GARCH fit failed; no substitute forecast", np.nan)
                        for m in ("garch_normal", "garch_fhs")
                    ]
                for method, estimate, warning, sigma in estimates:
                    loss = float(-series[pos])
                    var = estimate.var_fraction if estimate else np.nan
                    es = estimate.es_fraction if estimate else np.nan
                    rows.append(
                        {
                            "strategy": strategy,
                            "method": method,
                            "confidence": confidence,
                            "period": "validation"
                            if date < pd.Timestamp(policy.validation_end_exclusive)
                            else "evaluation",
                            "forecast_date": str(date.date()),
                            "as_of": str(as_of.date()),
                            "window_start": str(fit_start.date()),
                            "parameter_fit_end": str(fit_end.date()),
                            "reference_nav": policy.initial_capital,
                            "horizon_sessions": 1,
                            "var_fraction": var,
                            "es_fraction": es,
                            "loss_fraction": loss,
                            "exception": float(loss > var) if estimate else np.nan,
                            "sigma_fraction": sigma,
                            "regime": regime,
                            "status": "ok" if estimate else "unavailable",
                            "warning": warning,
                        }
                    )
            if fit:
                variances[strategy] = (
                    fit.omega
                    + fit.alpha * (series[pos] - fit.mean) ** 2
                    + fit.beta * variances[strategy]
                )
        residual = values[pos] - mean_vector
        covariance = settings.ewma_decay * covariance + (1 - settings.ewma_decay) * np.outer(
            residual, residual
        )
    forecasts = pd.DataFrame(rows)
    for name in ("var", "es", "loss"):
        forecasts[f"{name}_usd"] = forecasts[f"{name}_fraction"] * policy.initial_capital
    return forecasts, pd.DataFrame(fits), pd.DataFrame(correlations)
