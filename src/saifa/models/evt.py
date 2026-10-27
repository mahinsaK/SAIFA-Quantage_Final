"""Unconditional POT/GPD tails, threshold diagnostics and circular block bootstrap."""

from dataclasses import asdict
from math import ceil

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.stats import genpareto

from saifa.domain.config import EVTConfig
from saifa.domain.evt import POTEstimate, POTFit


def _losses(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Losses must be a finite one-dimensional sample of length >= 2")
    return values


def _optimizer(function, x0, args=(), disp=0):
    result = minimize(
        function,
        x0,
        args=args,
        method="Nelder-Mead",
        options={"maxiter": 5000, "xatol": 1e-9, "fatol": 1e-9},
    )
    if not result.success or not np.isfinite(result.fun):
        raise ValueError("GPD optimizer did not converge")
    return result.x


def fit_pot(losses: np.ndarray, quantile: float, minimum_exceedances: int = 50) -> POTFit:
    values = _losses(losses)
    if not np.isfinite(quantile) or not 0 < quantile < 1:
        raise ValueError("Threshold quantile must be in (0, 1)")
    if type(minimum_exceedances) is not int or minimum_exceedances < 2:
        raise ValueError("Minimum exceedances must be an integer >= 2")
    threshold = float(np.quantile(values, quantile, method="inverted_cdf"))
    excess = values[values > threshold] - threshold
    base = {
        "quantile": quantile,
        "threshold": threshold,
        "observations": len(values),
        "exceedances": len(excess),
        "mean_excess": float(excess.mean()) if len(excess) else None,
    }
    empty = {"shape": None, "scale": None, "modified_scale": None}
    if len(excess) < minimum_exceedances:
        return POTFit(
            **base,
            **empty,
            status="insufficient_exceedances",
            warning=f"Need {minimum_exceedances} strict exceedances; found {len(excess)}",
        )
    if np.unique(excess).size < 3:
        return POTFit(
            **base,
            **empty,
            status="degenerate_tail",
            warning="Fewer than three distinct excess values",
        )
    # Unit scaling improves numerical conditioning without changing the fitted distribution.
    unit = float(excess.mean())
    try:
        shape, _, scale = genpareto.fit(excess / unit, floc=0, optimizer=_optimizer)
        scale = float(scale * unit)
        shape = float(shape)
        if (
            not np.isfinite([shape, scale]).all()
            or scale <= 0
            or np.any(1 + shape * excess / scale <= 0)
            or not np.isfinite(genpareto.logpdf(excess, shape, scale=scale)).all()
        ):
            raise ValueError("Invalid fitted parameters or GPD support")
    except (ValueError, RuntimeError, FloatingPointError) as exc:
        return POTFit(**base, **empty, status="fit_failed", warning=str(exc))
    warning = "Unconditional tail; volatility clustering and regime changes remain"
    status = "ok"
    if shape <= -0.5:
        status = "nonregular_fit"
        warning += "; shape <= -0.5: nonregular MLE; risk estimates withheld"
    if shape >= 1:
        warning += "; shape >= 1: no finite GPD expected shortfall"
    elif shape >= 0.5:
        warning += "; fitted GPD variance is infinite"
    return POTFit(
        **base,
        shape=shape,
        scale=scale,
        modified_scale=scale - shape * threshold,
        status=status,
        warning=warning,
    )


def pot_tail(fit: POTFit, confidence: float) -> POTEstimate:
    """Evaluate the fitted tail, including its empirical threshold boundary.

    At c = 1 - N_u/n, VaR is u and ES is u + beta/(1-xi).
    This boundary VaR is empirical, not a GPD extrapolation into the body.
    """
    if not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("Confidence must be a finite fraction in (0, 1)")
    if fit.status != "ok":
        return POTEstimate(confidence, None, None, fit.status, fit.warning)
    probability = fit.exceedances / fit.observations
    boundary = 1 - probability
    at_boundary = np.isclose(confidence, boundary, rtol=0, atol=1e-12)
    if confidence < boundary and not at_boundary:
        return POTEstimate(
            confidence,
            None,
            None,
            "below_tail_domain",
            "Confidence is below the empirical CDF at the threshold; "
            "strict exceedance counts include the effect of ties",
        )
    xi, beta, u = fit.shape, fit.scale, fit.threshold
    log_ratio = 0.0 if at_boundary else np.log(probability / (1 - confidence))
    with np.errstate(over="ignore", invalid="ignore"):
        increment = beta * log_ratio if abs(xi) < 1e-8 else beta * np.expm1(xi * log_ratio) / xi
        var = float(u + increment)
        es = float((var + beta - xi * u) / (1 - xi)) if xi < 1 else None
    if not np.isfinite(var) or (es is not None and not np.isfinite(es)):
        return POTEstimate(confidence, None, None, "numerical_failure", "Nonfinite tail estimate")
    warning = fit.warning
    if at_boundary:
        warning += (
            "; Threshold-boundary estimate: VaR equals the empirical loss threshold; "
            "ES uses the fitted GPD tail mean, not extrapolated VaR"
        )
    if var > 1 or (es is not None and es > 1):
        warning += "; unbounded GPD implies loss above 100%; not clipped"
    return POTEstimate(confidence, var, es, "ok" if es is not None else "infinite_mean", warning)


def threshold_diagnostics(losses: np.ndarray, config: EVTConfig) -> tuple[POTFit, ...]:
    return tuple(
        fit_pot(losses, q, config.minimum_exceedances) for q in config.sensitivity_quantiles
    )


def qq_diagnostics(losses: np.ndarray, fit: POTFit) -> pd.DataFrame:
    values = _losses(losses)
    columns = ["probability", "observed_excess", "fitted_excess"]
    if fit.status != "ok":
        return pd.DataFrame(columns=columns)
    excess = np.sort(values[values > fit.threshold] - fit.threshold)
    probabilities = (np.arange(len(excess)) + 0.5) / len(excess)
    return pd.DataFrame(
        {
            "probability": probabilities,
            "observed_excess": excess,
            "fitted_excess": genpareto.ppf(probabilities, fit.shape, scale=fit.scale),
        }
    )


def circular_block_sample(
    values: np.ndarray, block_length: int, rng: np.random.Generator
) -> np.ndarray:
    values = _losses(values)
    if type(block_length) is not int or not 1 <= block_length <= len(values):
        raise ValueError("Block length must be between one and sample size")
    starts = rng.integers(0, len(values), size=ceil(len(values) / block_length))
    indices = (starts[:, None] + np.arange(block_length)) % len(values)
    return values[indices.ravel()[: len(values)]]


def bootstrap_tail(
    losses: np.ndarray, config: EVTConfig, confidences: tuple[float, ...]
) -> pd.DataFrame:
    values = _losses(losses)
    if config.block_length > len(values):
        raise ValueError("Bootstrap block length exceeds sample size")
    rng = np.random.Generator(np.random.PCG64(config.seed))
    records = []
    for replicate in range(config.bootstrap_replicates):
        sampled = circular_block_sample(values, config.block_length, rng)
        fit = fit_pot(sampled, config.threshold_quantile, config.minimum_exceedances)
        for confidence in confidences:
            records.append(
                dict(
                    replicate=replicate,
                    shape=fit.shape,
                    scale=fit.scale,
                    threshold=fit.threshold,
                    **asdict(pot_tail(fit, confidence)),
                )
            )
    return pd.DataFrame(records)


def bootstrap_intervals(draws: pd.DataFrame, point: POTEstimate) -> dict:
    """Avoid hiding failed or infinite-mean draws behind a finite ES interval."""
    group = draws.loc[draws.confidence.eq(point.confidence)]
    finite_var = np.isfinite(group.var_fraction.to_numpy(dtype=float))
    finite_es = np.isfinite(group.es_fraction.to_numpy(dtype=float))
    result = {
        "bootstrap_replicates": len(group),
        "var_valid_replicates": int(finite_var.sum()),
        "es_valid_replicates": int(finite_es.sum()),
        "var_ci_low": None,
        "var_ci_high": None,
        "es_ci_low": None,
        "es_ci_high": None,
        "shape_ci_low": None,
        "shape_ci_high": None,
        "scale_ci_low": None,
        "scale_ci_high": None,
    }
    warnings = []
    if len(group) < 200:
        warnings.append("Fewer than 200 bootstrap replicates; interval endpoints are coarse")
    if point.var_fraction is None or finite_var.mean() < 0.9:
        warnings.append("Intervals withheld: unavailable point estimate or >10% invalid VaR draws")
    else:
        for field in ("var", "shape", "scale"):
            values = group.loc[finite_var, "var_fraction" if field == "var" else field]
            low, high = np.quantile(values, [0.025, 0.975])
            result.update({f"{field}_ci_low": float(low), f"{field}_ci_high": float(high)})
        if point.es_fraction is not None and np.array_equal(finite_es, finite_var):
            low, high = np.quantile(group.loc[finite_es, "es_fraction"], [0.025, 0.975])
            result.update(es_ci_low=float(low), es_ci_high=float(high))
        else:
            warnings.append("ES interval withheld: at least one valid VaR draw has no finite ES")
        if not finite_var.all():
            warnings.append("Intervals conditional on successful fits; see invalid replicate count")
    result["interval_warning"] = "; ".join(warnings)
    return result
