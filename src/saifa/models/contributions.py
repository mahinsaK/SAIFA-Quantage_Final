"""Euler Normal attribution and a tie-symmetric empirical ES subgradient."""

import numpy as np
import pandas as pd
from scipy.stats import norm

from saifa.domain.config import OptimisationConfig
from saifa.domain.stress import AssetContribution, ContributionResult
from saifa.models.optimisation import validate_policy_weights
from saifa.models.risk import empirical_tail, fit_gaussian, normal_tail, ordered_weights


def _assets(columns, w, marginal, total):
    return tuple(
        AssetContribution(
            ticker=str(ticker),
            weight=float(w[i]),
            marginal_fraction=float(marginal[i]) if marginal is not None else None,
            component_fraction=float(w[i] * marginal[i]) if marginal is not None else None,
            share_percent=float(100 * w[i] * marginal[i] / total)
            if marginal is not None and abs(total) > 1e-12
            else None,
        )
        for i, ticker in enumerate(columns)
    )


def normal_contributions(
    returns: pd.DataFrame, weights: pd.Series, confidence: float
) -> tuple[ContributionResult, ...]:
    fit = fit_gaussian(returns)
    w = ordered_weights(weights, returns.columns)
    mu, covariance = fit.mean.to_numpy(), fit.covariance.to_numpy()
    covariance_with_portfolio = covariance @ w
    sigma = float(np.sqrt(max(w @ covariance_with_portfolio, 0)))
    tail = normal_tail(float(w @ mu), sigma, confidence)
    z = norm.ppf(confidence)
    results = []
    for measure, total, factor in (
        ("var", tail.var_fraction, z),
        ("es", tail.es_fraction, norm.pdf(z) / (1 - confidence)),
    ):
        warning = "Unconstrained exposure derivative; funded transfers require differences of marginals. Negative components retained."
        status = "ok"
        if sigma > 1e-12:
            marginal = -mu + factor * covariance_with_portfolio / sigma
        elif np.max(np.abs(covariance)) <= 1e-24:
            marginal = -mu
            warning += " Deterministic assets: contribution is negative expected return."
        else:
            marginal = None
            status = "undefined_gradient"
            warning += " Zero/near-zero portfolio volatility with risky assets: gradient is undefined/unstable."
        if abs(total) <= 1e-12:
            warning += " Near-zero total: percentage shares unavailable."
        results.append(
            ContributionResult(
                "parametric_normal",
                measure,
                confidence,
                total,
                _assets(returns.columns, w, marginal, total),
                status,
                warning,
            )
        )
    return tuple(results)


def historical_es_contributions(
    returns: pd.DataFrame, weights: pd.Series, confidence: float
) -> ContributionResult:
    fit_gaussian(returns)  # Shared finite/simple-return validation, not a Normal assumption.
    w = ordered_weights(weights, returns.columns)
    asset_losses = -returns.to_numpy(dtype=float)
    losses = asset_losses @ w
    tail = empirical_tail(losses, confidence)
    mass = len(losses) * (1 - confidence)
    above, boundary = losses > tail.var_fraction, losses == tail.var_fraction
    remainder = float(np.clip(mass - above.sum(), 0, boundary.sum()))
    probabilities = above.astype(float)
    probabilities[boundary] = remainder / boundary.sum()
    probabilities /= probabilities.sum()
    marginal = probabilities @ asset_losses
    warning = "Portfolio-tail conditional asset losses, not standalone asset ES."
    status = "ok"
    if boundary.sum() > 1 and 1e-10 < remainder < boundary.sum() - 1e-10:
        status = "tie_subgradient"
        warning += " Boundary ties share tail mass equally; selected subgradient may not be a unique derivative."
    if mass < 20:
        warning += " Fewer than 20 effective tail observations; attribution is sample-sensitive."
    if abs(tail.es_fraction) <= 1e-12:
        warning += " Near-zero total: percentage shares unavailable."
    if not np.isclose(w @ marginal, tail.es_fraction, rtol=1e-10, atol=1e-12):
        raise RuntimeError("Empirical ES contributions fail the additive identity")
    return ContributionResult(
        "historical",
        "es",
        confidence,
        tail.es_fraction,
        _assets(returns.columns, w, marginal, tail.es_fraction),
        status,
        warning,
        mass,
    )


def funded_transfer_checks(
    returns: pd.DataFrame,
    weights: pd.Series,
    confidence: float,
    step: float,
    policy: OptimisationConfig,
) -> pd.DataFrame:
    """Reprice prespecified funded one-percentage-point transfers; no automatic recommendation."""
    if not np.isfinite(step) or not 0 < step < 1:
        raise ValueError("Transfer step must be in (0, 1)")
    ordered_weights(weights, returns.columns)
    base = (
        *normal_contributions(returns, weights, confidence),
        historical_es_contributions(returns, weights, confidence),
    )
    rows = []
    for donor in weights.index:
        for receiver in weights.index:
            if donor == receiver:
                continue
            changed = weights.copy()
            changed[donor] -= step
            changed[receiver] += step
            reason = ""
            if (changed < 0).any():
                reason = "Insufficient donor weight"
            else:
                try:
                    validate_policy_weights(changed, policy)
                except ValueError as exc:
                    reason = str(exc)
            after = (
                (
                    *normal_contributions(returns, changed, confidence),
                    historical_es_contributions(returns, changed, confidence),
                )
                if not reason
                else (None,) * len(base)
            )
            for before, new in zip(base, after):
                marginals = {r.ticker: r.marginal_fraction for r in before.assets}
                approximate = (
                    step * (marginals[receiver] - marginals[donor])
                    if marginals[receiver] is not None and marginals[donor] is not None
                    else None
                )
                rows.append(
                    {
                        "donor": donor,
                        "receiver": receiver,
                        "transfer_weight": step,
                        "confidence": confidence,
                        "method": before.method,
                        "measure": before.measure,
                        "feasible": not bool(reason),
                        "reason": reason,
                        "before_fraction": before.total_fraction,
                        "after_fraction": new.total_fraction if new else None,
                        "delta_fraction": new.total_fraction - before.total_fraction
                        if new
                        else None,
                        "linear_delta_fraction": approximate if new else None,
                        "marginal_status": before.status,
                        "marginal_warning": before.warning,
                    }
                )
    return pd.DataFrame(rows)
