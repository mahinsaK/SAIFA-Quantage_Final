"""Training-only sensitivity; no evaluation-return-driven choice of settings."""

import numpy as np
import pandas as pd

from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.domain.research import ResearchConfig
from saifa.models.optimisation import annualised_inputs, optimise_portfolio
from saifa.models.research.allocations import checked_optimisation


def block_indices(
    size: int,
    length: int,
    paths: int,
    mean_block: int,
    seed: int,
    consecutive: np.ndarray | None = None,
) -> np.ndarray:
    """Geometric block resampling; optional calendar gaps force a fresh start."""
    if min(size, length, paths, mean_block) < 1 or seed < 0:
        raise ValueError("Invalid block resampling dimensions")
    if consecutive is not None and len(consecutive) != size:
        raise ValueError("Calendar-continuity flags must match sample size")
    rng = np.random.default_rng(seed)
    indices = np.empty((paths, length), dtype=int)
    indices[:, 0] = rng.integers(size, size=paths)
    for t in range(1, length):
        previous = indices[:, t - 1]
        restart = rng.random(paths) < 1 / mean_block
        if consecutive is not None:
            restart |= ~consecutive[previous]
        indices[:, t] = np.where(restart, rng.integers(size, size=paths), (previous + 1) % size)
    return indices


def allocation_robustness(
    returns: pd.DataFrame,
    rates: pd.Series,
    reference: pd.DataFrame,
    policy: OptimisationConfig,
    settings: ResearchConfig,
) -> pd.DataFrame:
    training = returns.loc[returns.index < policy.development_end_exclusive]
    means, cov = annualised_inputs(training, policy.annual_trading_days)
    rf = rates.reindex(training.index)
    if not np.isfinite(rf.to_numpy()).all():
        raise ValueError("Robustness training rates are incomplete")
    rate = float(rf.mean() * policy.annual_trading_days)
    variants = [("full_development", means, cov, rate, len(training), "prespecified")]
    cutoff = pd.Timestamp(policy.development_end_exclusive)
    for years in (5, 10):
        subset = training.loc[training.index >= cutoff - pd.DateOffset(years=years)]
        m, c = annualised_inputs(subset, policy.annual_trading_days)
        variants.append(
            (
                f"trailing_{years}_years",
                m,
                c,
                float(rf.loc[subset.index].mean() * policy.annual_trading_days),
                len(subset),
                "prespecified",
            )
        )
    subset = training.loc[training.index < cutoff - pd.DateOffset(years=1)]
    m, c = annualised_inputs(subset, policy.annual_trading_days)
    variants.append(
        (
            "end_one_year_earlier",
            m,
            c,
            float(rf.loc[subset.index].mean() * policy.annual_trading_days),
            len(subset),
            "prespecified",
        )
    )
    for shift in (-0.02, 0.02):
        changed = means.copy()
        changed["SPY"] += shift
        variants.append(
            (f"SPY_mean_{shift:+.0%}", changed, cov, rate, len(training), "prespecified")
        )
    diagonal = np.diag(np.diag(cov))
    variants.append(
        (
            "25pct_diagonal_shrinkage",
            means,
            0.75 * cov + 0.25 * diagonal,
            rate,
            len(training),
            "prespecified",
        )
    )
    bootstrap = block_indices(
        len(training),
        len(training),
        settings.robustness_replicates,
        settings.robustness_block,
        settings.seed,
    )
    for i, rows in enumerate(bootstrap):
        sampled = training.iloc[rows]
        m, c = annualised_inputs(sampled, policy.annual_trading_days)
        variants.append(
            (
                f"block_{i:03d}",
                m,
                c,
                float(rf.iloc[rows].mean() * policy.annual_trading_days),
                len(sampled),
                "block_resample",
            )
        )
    records = []
    for name, m, c, r, n, kind in variants:
        for objective in ("minimum_volatility", "maximum_sharpe"):
            base = {
                "strategy": objective,
                "variant": name,
                "kind": kind,
                "observations": n,
                "training_end_exclusive": policy.development_end_exclusive,
            }
            try:
                weights = checked_optimisation(
                    optimise_portfolio(objective, m, c, r, policy), policy
                )
                original = reference.loc[objective, list(UNIVERSE)]
                difference = weights - original
                records.append(
                    {
                        **base,
                        "status": "ok",
                        "reason": "",
                        "one_way_weight_distance": float(difference.abs().sum() / 2),
                        "maximum_asset_weight_change": float(difference.abs().max()),
                        **weights.to_dict(),
                    }
                )
            except (RuntimeError, ValueError) as exc:
                records.append(
                    {
                        **base,
                        "status": "unavailable",
                        "reason": str(exc),
                        "one_way_weight_distance": np.nan,
                        "maximum_asset_weight_change": np.nan,
                        **dict.fromkeys(UNIVERSE, np.nan),
                    }
                )
    return pd.DataFrame(records)
