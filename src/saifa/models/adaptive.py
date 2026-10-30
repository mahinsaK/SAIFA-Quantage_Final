"""Annual targets fitted only on preceding calendar years, executed at the next close."""

import numpy as np
import pandas as pd

from saifa.domain.adaptive import AdaptiveConfig
from saifa.domain.config import UNIVERSE
from saifa.models.optimisation import annualised_inputs, optimise_portfolio, validate_policy_weights


def fit_annual_targets(
    execution_dates: pd.DatetimeIndex,
    returns: pd.DataFrame,
    risk_free: pd.Series,
    config: AdaptiveConfig,
) -> pd.DataFrame:
    """One pair of fits per year; no evaluation-session returns enter that year's fit."""
    for index in (execution_dates, returns.index, risk_free.index):
        if (
            not isinstance(index, pd.DatetimeIndex)
            or index.empty
            or index.hasnans
            or not index.is_unique
            or not index.is_monotonic_increasing
            or index.tz is not None
        ):
            raise ValueError("Annual refitting requires unique ordered timezone-naive dates")
    if tuple(returns.columns) != UNIVERSE:
        raise ValueError("Annual refitting requires all seven eligible ETFs in order")
    if execution_dates.year.duplicated().any():
        raise ValueError("Only one annual target update per year is supported")
    records = []
    for execution in execution_dates:
        cutoff = pd.Timestamp(execution.year, 1, 1)
        start = pd.Timestamp(execution.year - config.lookback_years, 1, 1)
        training = returns.loc[(returns.index >= start) & (returns.index < cutoff)]
        if len(training) < config.minimum_observations:
            raise ValueError(
                f"Insufficient trailing history for {execution.date()}: {len(training)} observations"
            )
        if (
            training.index[0].year != start.year
            or training.index[0].month != 1
            or training.index[-1].year != execution.year - 1
            or training.index[-1].month != 12
        ):
            raise ValueError(f"Incomplete calendar-year training coverage for {execution.date()}")
        rates = risk_free.reindex(training.index)
        if not np.isfinite(rates.to_numpy(dtype=float)).all():
            raise ValueError(f"Missing training risk-free rates for {execution.date()}")
        means, covariance = annualised_inputs(training, config.portfolio.annual_trading_days)
        annual_rate = float(rates.mean() * config.portfolio.annual_trading_days)
        for objective in ("minimum_volatility", "maximum_sharpe"):
            candidate = optimise_portfolio(
                objective, means, covariance, annual_rate, config.portfolio
            )
            if not candidate.success:
                raise RuntimeError(
                    f"Annual {objective} fit failed for {execution.date()}: {candidate.message}"
                )
            # Solver feasibility tolerances and tiny-weight clipping can leave a
            # near-unit sum. Record it and fund an exactly unit-sum target.
            validate_policy_weights(candidate.weights, config.portfolio)
            solver_sum = float(candidate.weights.sum())
            weights = candidate.weights / solver_sum
            validate_policy_weights(weights, config.portfolio)
            expected = float(weights @ means)
            volatility = float(np.sqrt(weights @ covariance @ weights))
            records.append(
                {
                    "strategy": f"annual_{candidate.name}",
                    "execution_date": execution.date().isoformat(),
                    "training_start": training.index[0].date().isoformat(),
                    "training_end": training.index[-1].date().isoformat(),
                    "training_start_inclusive": start.date().isoformat(),
                    "training_end_exclusive": cutoff.date().isoformat(),
                    "observations": len(training),
                    "annual_risk_free": annual_rate,
                    "solver_weight_sum": solver_sum,
                    "expected_return": expected,
                    "estimated_volatility": volatility,
                    "estimated_sharpe": (expected - annual_rate) / volatility
                    if volatility > 0
                    else np.nan,
                    "solver_success": candidate.success,
                    "solver_message": candidate.message,
                    **weights.to_dict(),
                }
            )
    return pd.DataFrame(records)


def annual_execution_dates(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First observed session of each calendar year, including the initial allocation."""
    if dates.empty or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("Ordered nonempty price dates required")
    return dates[~dates.year.duplicated()]
