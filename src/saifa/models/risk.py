"""Historical and Gaussian VaR/ES on signed one-session portfolio losses."""

import numpy as np
import pandas as pd
from scipy.stats import norm

from saifa.domain.config import RiskConfig
from saifa.domain.risk import GaussianFit, RiskEstimate, TailEstimate


def _confidence(confidence: float) -> None:
    if not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("Confidence must be a finite fraction in (0, 1)")


def empirical_tail(losses: np.ndarray, confidence: float) -> TailEstimate:
    """Inverse empirical CDF VaR and integral-quantile ES, including boundary mass."""
    _confidence(confidence)
    values = np.asarray(losses, dtype=float)
    if values.ndim != 1 or not values.size or not np.isfinite(values).all():
        raise ValueError("Losses must be a nonempty finite one-dimensional sample")
    ordered = np.sort(values)
    var = float(np.quantile(ordered, confidence, method="inverted_cdf"))
    # Each sorted observation spans [i/n, (i+1)/n] in the empirical quantile function.
    # Fractional overlap with [confidence, 1] handles noninteger tail counts and ties.
    n = len(ordered)
    boundary = confidence * n
    mass = np.clip(np.arange(1, n + 1) - boundary, 0.0, 1.0)
    es = float(ordered @ mass / mass.sum())
    return TailEstimate(var, es)


def normal_tail(mean_return: float, volatility: float, confidence: float) -> TailEstimate:
    """Return moments are daily decimal units; positive loss = negative return."""
    _confidence(confidence)
    if not np.isfinite([mean_return, volatility]).all() or volatility < 0:
        raise ValueError("Mean and nonnegative volatility must be finite")
    z = norm.ppf(confidence)
    return TailEstimate(
        float(-mean_return + volatility * z),
        float(-mean_return + volatility * norm.pdf(z) / (1 - confidence)),
    )


def select_risk_window(returns: pd.DataFrame, config: RiskConfig) -> pd.DataFrame:
    """Use close information available at as_of, for the following session only."""
    if (
        not isinstance(returns.index, pd.DatetimeIndex)
        or returns.empty
        or not returns.index.is_unique
        or not returns.index.is_monotonic_increasing
        or returns.index.tz is not None
        or not returns.index.equals(returns.index.normalize())
    ):
        raise ValueError("Returns require unique ordered naive session dates")
    as_of = pd.Timestamp(config.as_of) if config.as_of else returns.index[-1]
    if as_of not in returns.index:
        raise ValueError("As-of date must be an observed trading session")
    selected = returns.loc[:as_of].tail(config.lookback_observations).copy()
    if len(selected) != config.lookback_observations:
        raise ValueError("Insufficient history for the requested lookback; no shorter fallback")
    return selected


def fit_gaussian(asset_returns: pd.DataFrame) -> GaussianFit:
    if (
        len(asset_returns) < 2
        or asset_returns.shape[1] == 0
        or not asset_returns.columns.is_unique
        or not np.isfinite(asset_returns.to_numpy(dtype=float)).all()
        or (asset_returns < -1).any().any()
    ):
        raise ValueError("Asset simple returns must be finite, >= -1, with unique columns")
    return GaussianFit(asset_returns.mean(), asset_returns.cov(ddof=1), len(asset_returns))


def ordered_weights(weights: pd.Series, assets: pd.Index) -> np.ndarray:
    if not weights.index.is_unique or set(weights.index) != set(assets):
        raise ValueError("Weights must match each asset exactly once")
    values = weights.reindex(assets).to_numpy(dtype=float)
    if (
        not np.isfinite(values).all()
        or (values < 0).any()
        or not np.isclose(values.sum(), 1, rtol=0, atol=1e-8)
    ):
        raise ValueError("Weights must be finite, long-only and sum to one")
    return values


def gaussian_scenarios(fit: GaussianFit, count: int, seed: int) -> np.ndarray:
    """Correlated asset scenarios, with an explicit local PCG64 random generator."""
    if type(count) is not int or count < 2 or type(seed) is not int or seed < 0:
        raise ValueError("Scenario count >= 2 and nonnegative integer seed required")
    covariance = fit.covariance.to_numpy(dtype=float)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    if eigenvalues.min() < -1e-12:
        raise ValueError("Covariance is not positive semidefinite")
    # Sample covariance can be singular; clip round-off-negative eigenvalues only.
    root = eigenvectors * np.sqrt(np.maximum(eigenvalues, 0))
    rng = np.random.Generator(np.random.PCG64(seed))
    standard = rng.standard_normal((count, len(fit.mean)))
    return standard @ root.T + fit.mean.to_numpy()


def compare_risk(
    asset_returns: pd.DataFrame,
    portfolios: dict[str, pd.Series],
    config: RiskConfig,
) -> tuple[RiskEstimate, ...]:
    """All methods share the same window, holdings, units and one-day horizon."""
    if not portfolios:
        raise ValueError("At least one portfolio is required")
    if len(asset_returns) != config.lookback_observations:
        raise ValueError("Risk sample length differs from configured lookback")
    fit = fit_gaussian(asset_returns)
    scenarios = gaussian_scenarios(fit, config.simulations, config.seed)
    estimates = []
    for strategy, weights in portfolios.items():
        w = ordered_weights(weights, asset_returns.columns)
        observed = asset_returns.to_numpy() @ w
        simulated = scenarios @ w
        mean = float(w @ fit.mean.to_numpy())
        sigma = float(np.sqrt(max(w @ fit.covariance.to_numpy() @ w, 0)))
        for confidence in config.confidence_levels:
            historical = empirical_tail(-observed, confidence)
            parametric = normal_tail(mean, sigma, confidence)
            monte_carlo = empirical_tail(-simulated, confidence)
            for method, tail in (
                ("historical", historical),
                ("parametric_normal", parametric),
                ("monte_carlo_normal", monte_carlo),
            ):
                warnings = []
                tail_count = None
                var_se = es_se = None
                if method == "historical":
                    tail_count = round(len(observed) * (1 - confidence), 12)
                    if tail_count < 20:
                        warnings.append("Fewer than 20 effective historical tail observations")
                if method == "monte_carlo_normal":
                    tail_count = round(config.simulations * (1 - confidence), 12)
                    if tail_count < 100:
                        warnings.append("Fewer than 100 effective simulated tail observations")
                    # Conditional simulation errors, not parameter/model uncertainty.
                    var_se = float(
                        sigma
                        * np.sqrt(confidence * (1 - confidence) / config.simulations)
                        / norm.pdf(norm.ppf(confidence))
                    )
                    excess = np.maximum(-simulated - tail.var_fraction, 0)
                    es_se = float(
                        excess.std(ddof=1) / ((1 - confidence) * np.sqrt(config.simulations))
                    )
                    if (simulated < -1).any():
                        warnings.append("Gaussian simulation produced portfolio losses above 100%")
                if method != "historical":
                    warnings.append("Gaussian tails; no volatility clustering or fat-tail model")
                estimates.append(
                    RiskEstimate(
                        strategy=strategy,
                        method=method,
                        confidence=confidence,
                        horizon_sessions=config.horizon_sessions,
                        reference_nav=config.reference_nav,
                        observations=len(asset_returns),
                        var_fraction=tail.var_fraction,
                        es_fraction=tail.es_fraction,
                        var_percent=100 * tail.var_fraction,
                        es_percent=100 * tail.es_fraction,
                        var_usd=config.reference_nav * tail.var_fraction,
                        es_usd=config.reference_nav * tail.es_fraction,
                        scenarios=config.simulations if method == "monte_carlo_normal" else None,
                        seed=config.seed if method == "monte_carlo_normal" else None,
                        effective_tail_observations=tail_count,
                        mc_var_standard_error=var_se,
                        mc_es_standard_error=es_se,
                        warning="; ".join(warnings),
                    )
                )
    return tuple(estimates)
