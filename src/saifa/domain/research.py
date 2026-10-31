"""Explicit settings and result types for retrospective research extensions."""

from dataclasses import dataclass

import pandas as pd

RESEARCH_PORTFOLIOS = {
    "baseline_40_60": "40/60 baseline",
    "minimum_volatility": "Frozen minimum volatility",
    "maximum_sharpe": "Frozen maximum Sharpe",
    "minimum_es": "Minimum historical ES (95%)",
    "risk_parity": "Constrained risk parity",
}
VOLATILITY_METHODS = {
    "garch_normal": "GARCH(1,1) · Normal",
    "garch_fhs": "GARCH · filtered historical",
    "ewma_normal": "EWMA covariance · Normal",
}
RESEARCH_TABLES = (
    "allocation_weights",
    "allocation_diagnostics",
    "candidate_metrics",
    "candidate_daily",
    "candidate_transactions",
    "robustness_weights",
    "volatility_forecasts",
    "volatility_fits",
    "volatility_tests",
    "correlations",
    "spending_summary",
    "spending_fan",
    "spending_inputs",
    "cost_metrics",
    "liquidity",
    "income_summary",
    "income_ledger",
    "availability",
)


@dataclass(frozen=True)
class ResearchConfig:
    es_confidence: float = 0.95
    robustness_replicates: int = 30
    robustness_block: int = 20
    volatility_lookback: int = 1000
    ewma_decay: float = 0.94
    spending_paths: int = 1000
    spending_months: int = 120
    spending_block: int = 6
    seed: int = 20261030

    def __post_init__(self):
        if self.es_confidence != 0.95:
            raise ValueError("This prespecified research allocation uses 95% ES")
        if not 0 < self.es_confidence < 1 or not 0 < self.ewma_decay < 1:
            raise ValueError("Tail confidence and EWMA decay must be in (0, 1)")
        for key, minimum in (
            ("robustness_replicates", 2),
            ("robustness_block", 1),
            ("volatility_lookback", 252),
            ("spending_paths", 20),
            ("spending_months", 12),
            ("spending_block", 1),
            ("seed", 0),
        ):
            if type(getattr(self, key)) is not int or getattr(self, key) < minimum:
                raise ValueError(f"{key} must be an integer >= {minimum}")


@dataclass(frozen=True)
class ResearchEvidence:
    summary: dict
    tables: dict[str, pd.DataFrame]


@dataclass(frozen=True)
class GarchFit:
    mean: float
    omega: float
    alpha: float
    beta: float
    next_variance: float
    standardized_residuals: tuple[float, ...]
    message: str
