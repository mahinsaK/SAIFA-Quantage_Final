"""Checked display data for committee-facing charts; no financial refitting."""

import numpy as np
import pandas as pd

from saifa.domain.config import UNIVERSE
from saifa.domain.dashboard import STRATEGIES, DashboardDataError


def observed_growth_chart_data(observed: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    required = {
        "strategy",
        "start_date",
        "end_date",
        "annualised_real_growth",
        "objective",
    }
    if not required.issubset(observed) or observed.strategy.duplicated().any():
        raise DashboardDataError("Observed real-growth comparison is incomplete")
    if set(observed.strategy) != set(STRATEGIES):
        raise DashboardDataError("Observed real-growth comparison needs all three portfolios")
    if any(observed[col].nunique() != 1 for col in ("start_date", "end_date", "objective")):
        raise DashboardDataError("Observed real-growth periods or objectives differ")
    values = observed.set_index("strategy").loc[list(STRATEGIES)].copy()
    if not np.isfinite(values[["annualised_real_growth", "objective"]].to_numpy(dtype=float)).all():
        raise DashboardDataError("Observed real-growth values are unavailable")
    result = pd.DataFrame(
        {
            "Portfolio": [STRATEGIES[name] for name in STRATEGIES],
            "Real growth (% / year)": values.annualised_real_growth.to_numpy(dtype=float) * 100,
        }
    )
    return result, float(values.objective.iloc[0] * 100)


def crisis_drawdown_chart_data(summary: pd.DataFrame) -> tuple[pd.DataFrame, float, int]:
    required = {
        "strategy",
        "scenario",
        "status",
        "maximum_drawdown_fraction",
        "drawdown_review_level",
    }
    if not required.issubset(summary) or summary.duplicated(["strategy", "scenario"]).any():
        raise DashboardDataError("Crisis comparison is incomplete or duplicated")
    valid = summary.loc[summary.status == "ok"].copy()
    if valid.empty:
        raise DashboardDataError("No complete crisis replay is available")
    numeric = valid[["maximum_drawdown_fraction", "drawdown_review_level"]].to_numpy(dtype=float)
    if (
        not np.isfinite(numeric).all()
        or (valid.maximum_drawdown_fraction < 0).any()
        or (valid.maximum_drawdown_fraction > 1).any()
        or valid.drawdown_review_level.nunique() != 1
    ):
        raise DashboardDataError("Crisis drawdowns or review levels cannot share one chart")
    labels = {
        "2008_GFC": "2008 GFC",
        "March_2020": "March 2020",
        "2022_rate_shock": "2022 rate shock",
    }
    result = pd.DataFrame(
        {
            "Crisis": valid.scenario.map(lambda value: labels.get(value, value)),
            "Portfolio": valid.strategy.map(STRATEGIES),
            "Maximum drawdown (%)": valid.maximum_drawdown_fraction.to_numpy(dtype=float) * 100,
        }
    )
    if result.Portfolio.isna().any():
        raise DashboardDataError("Crisis comparison has an unknown portfolio")
    return result, float(valid.drawdown_review_level.iloc[0] * 100), len(summary) - len(valid)


def risk_contribution_chart_data(
    assets: pd.DataFrame, totals: pd.DataFrame, strategy: str, confidence: float, method: str
) -> pd.DataFrame:
    """Use only defined attribution methods and measures; keep signed offsets."""
    measures = {"historical": ("es",), "parametric_normal": ("var", "es")}.get(method)
    if measures is None:
        raise DashboardDataError("Selected risk method has no supported attribution")
    needed_assets = {"strategy", "confidence", "method", "measure", "ticker", "component_usd"}
    needed_totals = {"strategy", "confidence", "method", "measure", "status"}
    if not needed_assets.issubset(assets) or not needed_totals.issubset(totals):
        raise DashboardDataError("Risk contribution evidence is incomplete")
    selected = assets.loc[
        (assets.strategy == strategy)
        & (assets.confidence == confidence)
        & (assets.method == method)
    ].copy()
    selected_totals = totals.loc[
        (totals.strategy == strategy)
        & (totals.confidence == confidence)
        & (totals.method == method)
    ]
    if (
        len(selected) != len(UNIVERSE) * len(measures)
        or selected.duplicated(["ticker", "measure"]).any()
        or set(selected.ticker) != set(UNIVERSE)
        or set(selected.measure) != set(measures)
        or len(selected_totals) != len(measures)
        or set(selected_totals.measure) != set(measures)
        or not selected_totals.status.eq("ok").all()
        or not np.isfinite(selected.component_usd.to_numpy(dtype=float)).all()
    ):
        raise DashboardDataError("Selected risk contributions are incomplete or unavailable")
    return pd.DataFrame(
        {
            "ETF": selected.ticker,
            "Measure": selected.measure.str.upper(),
            "Contribution (USD)": selected.component_usd.to_numpy(dtype=float),
        }
    )
