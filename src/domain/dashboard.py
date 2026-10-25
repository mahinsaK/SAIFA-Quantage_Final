"""Dashboard presentation contract; calculation assumptions stay in existing configs."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

CONFIDENCES = (0.90, 0.95, 0.99)
STRATEGIES = {
    "baseline_40_60": "40/60 baseline",
    "minimum_volatility": "Minimum volatility",
    "maximum_sharpe": "Maximum Sharpe",
}
METHODS = {
    "historical": "Historical",
    "parametric_normal": "Parametric Normal",
    "monte_carlo_normal": "Gaussian Monte Carlo",
    "evt_pot_gpd": "EVT · POT/GPD",
}
# Only these explicitly named files can be consumed; no newest-directory guessing.
TABLES = {
    "portfolio": (
        "evaluation_daily",
        "evaluation_metrics",
        "performance_ratios",
        "candidate_weights",
        "efficient_frontier",
    ),
    "risk": (
        "risk_comparison",
        "portfolio_weights",
        "threshold_diagnostics",
        "threshold_sensitivity",
    ),
    "backtest": ("forecasts",),
    "stress": (
        "contribution_summary",
        "asset_contributions",
        "sizing_checks",
        "historical_summary",
        "historical_paths",
        "hypothetical_summary",
        "hypothetical_components",
        "scenario_shocks",
        "portfolio_weights",
    ),
    "data": (),
}


class DashboardDataError(ValueError):
    """A result bundle is missing, inconsistent or unverified."""


@dataclass(frozen=True)
class DashboardBundle:
    manifest_path: Path
    manifest: dict
    metadata: dict[str, dict]
    tables: dict[str, dict[str, pd.DataFrame]]


@dataclass(frozen=True)
class BacktestView:
    forecasts: pd.DataFrame
    tests: pd.DataFrame
    lights: pd.DataFrame
