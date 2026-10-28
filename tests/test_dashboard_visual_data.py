"""Chart inputs preserve model availability, review levels and signed contributions."""

import pandas as pd
import pytest

from saifa.dashboard.visual_data import (
    crisis_drawdown_chart_data,
    observed_growth_chart_data,
    risk_contribution_chart_data,
)
from saifa.domain.config import UNIVERSE
from saifa.domain.dashboard import STRATEGIES, DashboardDataError


def test_observed_growth_chart_uses_same_period_and_objective():
    observed = pd.DataFrame(
        [
            {
                "strategy": strategy,
                "start_date": "2022-01-03",
                "end_date": "2026-09-30",
                "annualised_real_growth": growth,
                "objective": 0.03,
            }
            for strategy, growth in zip(STRATEGIES, (0.0068, 0.0254, 0.0271))
        ]
    )
    chart, objective = observed_growth_chart_data(observed)
    assert chart["Real growth (% / year)"].tolist() == pytest.approx([0.68, 2.54, 2.71])
    assert objective == pytest.approx(3.0)
    changed = observed.copy()
    changed.loc[2, "end_date"] = "2026-10-22"
    with pytest.raises(DashboardDataError, match="periods"):
        observed_growth_chart_data(changed)


def test_crisis_chart_keeps_review_level_and_omits_failed_replay():
    summary = pd.DataFrame(
        [
            {
                "strategy": "baseline_40_60",
                "scenario": "2008_GFC",
                "status": "ok",
                "maximum_drawdown_fraction": 0.217,
                "drawdown_review_level": 0.15,
            },
            {
                "strategy": "minimum_volatility",
                "scenario": "March_2020",
                "status": "ok",
                "maximum_drawdown_fraction": 0.117,
                "drawdown_review_level": 0.15,
            },
            {
                "strategy": "maximum_sharpe",
                "scenario": "2022_rate_shock",
                "status": "missing",
                "maximum_drawdown_fraction": float("nan"),
                "drawdown_review_level": 0.15,
            },
        ]
    )
    chart, review_level, omitted = crisis_drawdown_chart_data(summary)
    assert chart.Crisis.tolist() == ["2008 GFC", "March 2020"]
    assert chart["Maximum drawdown (%)"].tolist() == pytest.approx([21.7, 11.7])
    assert review_level == pytest.approx(15)
    assert omitted == 1
    changed = summary.copy()
    changed.loc[1, "drawdown_review_level"] = 0.10
    with pytest.raises(DashboardDataError, match="review levels"):
        crisis_drawdown_chart_data(changed)


def test_risk_contribution_chart_preserves_negative_offsets_and_method_boundary():
    assets = pd.DataFrame(
        [
            {
                "strategy": "baseline_40_60",
                "confidence": 0.99,
                "method": "parametric_normal",
                "measure": measure,
                "ticker": ticker,
                "component_usd": -1000 if ticker == "AGG" else 5000,
            }
            for measure in ("var", "es")
            for ticker in UNIVERSE
        ]
    )
    totals = pd.DataFrame(
        [
            {
                "strategy": "baseline_40_60",
                "confidence": 0.99,
                "method": "parametric_normal",
                "measure": measure,
                "status": "ok",
            }
            for measure in ("var", "es")
        ]
    )
    chart = risk_contribution_chart_data(
        assets, totals, "baseline_40_60", 0.99, "parametric_normal"
    )
    assert len(chart) == len(UNIVERSE) * 2
    assert set(chart.loc[chart.ETF == "AGG", "Contribution (USD)"]) == {-1000}
    with pytest.raises(DashboardDataError, match="no supported attribution"):
        risk_contribution_chart_data(assets, totals, "baseline_40_60", 0.99, "evt_pot_gpd")
    totals.loc[1, "status"] = "undefined"
    with pytest.raises(DashboardDataError, match="unavailable"):
        risk_contribution_chart_data(assets, totals, "baseline_40_60", 0.99, "parametric_normal")
