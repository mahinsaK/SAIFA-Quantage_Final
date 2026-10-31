"""Prespecified annual refitting experiment; not a client-approved strategy."""

from dataclasses import dataclass, field

import pandas as pd

from saifa.domain.config import OptimisationConfig

ADAPTIVE_STRATEGIES = {
    "baseline_40_60": "40/60 baseline",
    "minimum_volatility": "Frozen minimum volatility",
    "maximum_sharpe": "Frozen maximum Sharpe",
    "annual_minimum_volatility": "Annual minimum volatility",
    "annual_maximum_sharpe": "Annual maximum Sharpe",
}
ADAPTIVE_TABLES = ("annual_targets", "metrics", "daily", "transactions", "comparison")


@dataclass(frozen=True)
class AdaptiveConfig:
    portfolio: OptimisationConfig = field(default_factory=OptimisationConfig)
    lookback_years: int = 5
    minimum_observations: int = 1000

    def __post_init__(self) -> None:
        if type(self.lookback_years) is not int or self.lookback_years < 1:
            raise ValueError("Lookback must be a positive integer number of calendar years")
        if (
            type(self.minimum_observations) is not int
            or self.minimum_observations < self.portfolio.annual_trading_days
        ):
            raise ValueError("Minimum observations must cover at least one trading year")


@dataclass(frozen=True)
class AdaptiveEvidence:
    summary: dict
    tables: dict[str, pd.DataFrame]
