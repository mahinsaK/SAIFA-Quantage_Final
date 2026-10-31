"""Verified artifact loading and control-dependent research panels, without a browser."""

import json
from dataclasses import asdict

import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from test_dashboard import app_test
from test_dashboard import forecasts as forecasts  # noqa: PLC0414 - fixture export
from test_dashboard import prepared as prepared  # noqa: PLC0414 - fixture export

from saifa.application.research_pipeline import publish_research
from saifa.dashboard.data import load_bundle
from saifa.dashboard.research_data import load_research
from saifa.data.snapshots import file_hash, write_json
from saifa.domain.config import UNIVERSE
from saifa.domain.dashboard import STRATEGIES, DashboardDataError
from saifa.domain.research import (
    RESEARCH_PORTFOLIOS,
    RESEARCH_TABLES,
    VOLATILITY_METHODS,
    ResearchConfig,
)


@pytest.fixture
def research(prepared):
    root, path, _ = prepared
    bundle = load_bundle(root, path)
    tables = {name: pd.DataFrame({"fixture": [1]}) for name in RESEARCH_TABLES}
    weights = []
    diagnostics = []
    metrics = []
    daily = []
    costs = []
    incomes = []
    fans = []
    spending = []
    for i, strategy in enumerate(RESEARCH_PORTFOLIOS):
        w = {t: 0.0 for t in UNIVERSE}
        w.update(SPY=0.4, AGG=0.6)
        if strategy == "minimum_es":
            w.update(SPY=0.2, GLD=0.2)
        weights.append({"strategy": strategy, **w, **{f"risk_share_{t}": v for t, v in w.items()}})
        diagnostics.append(
            {
                "strategy": strategy,
                "development_es_fraction": 0.01,
                "equal_risk_achieved": False,
                "maximum_risk_share_gap": 0.1,
            }
        )
        incomes.append(
            {
                "strategy": strategy,
                "start_date": "2022-01-03",
                "end_date": "2022-12-30",
                "reference_nav": 1e7,
                "distribution_proxy_usd": 1000 if i == 0 else np.nan,
                "status": "proxy_only" if i == 0 else "unavailable",
                "reason": "split-unit review pending",
            }
        )
        for period, start, end, extra in [
            ("validation", "2021-11-01", "2021-12-31", 0.1),
            ("evaluation", "2022-01-03", "2022-12-30", 0),
        ]:
            row = {
                "period": period,
                "strategy": strategy,
                "start_date": start,
                "end_date": end,
                "initial_capital": 1e7,
                "ending_value": 1e7 * (1.02 + i * 0.01 + extra),
                "annualised_return": 0.03 + i * 0.01,
                "annualised_volatility": 0.08,
                "maximum_drawdown": -0.15,
                "total_transaction_cost": 10000.0,
            }
            metrics.append(row)
            daily += [
                {"period": period, "strategy": strategy, "Date": start, "nav": 1e7},
                {"period": period, "strategy": strategy, "Date": end, "nav": row["ending_value"]},
            ]
            for bps in (0.0, 10.0, 25.0):
                for fee in (0.0, 25.0, 50.0):
                    costs.append(
                        {
                            **row,
                            "trade_cost_bps": bps,
                            "additional_annual_fee_bps": fee,
                            "total_additional_fees": fee * 100,
                            "ending_value": row["ending_value"] * (1 - bps / 1e4 - fee / 1e4),
                        }
                    )
        if strategy in STRATEGIES:
            for rate in (0.02, 0.03, 0.04):
                for uplift in (0.0, 0.02):
                    ending = 1e7 * (1 - rate - uplift + i * 0.01)
                    spending.append(
                        {
                            "strategy": strategy,
                            "withdrawal_rate": rate,
                            "inflation_annual_spread": uplift,
                            "paths": 1000,
                            "months": 12,
                            "no_shortfall_fraction": 0.95,
                            "conditional_wilson_low": 0.9,
                            "conditional_wilson_high": 0.99,
                            "ending_real_p05": ending - 1e6,
                            "ending_real_median": ending,
                            "ending_real_p95": ending + 1e6,
                            "preserved_real_capital_fraction": 0.5,
                            "after_spending_3pct_growth_fraction": 0.3,
                        }
                    )
                    fans += [
                        {
                            "strategy": strategy,
                            "withdrawal_rate": rate,
                            "inflation_annual_spread": uplift,
                            "month": m,
                            "real_p05": ending - 1e6,
                            "real_median": ending,
                            "real_p95": ending + 1e6,
                        }
                        for m in range(13)
                    ]
    tables.update(
        allocation_weights=pd.DataFrame(weights),
        allocation_diagnostics=pd.DataFrame(diagnostics),
        candidate_metrics=pd.DataFrame(metrics),
        candidate_daily=pd.DataFrame(daily),
        cost_metrics=pd.DataFrame(costs),
        spending_summary=pd.DataFrame(spending),
        spending_fan=pd.DataFrame(fans),
        income_summary=pd.DataFrame(incomes),
    )
    prototype = bundle.tables["backtest"]["forecasts"].query("method == 'historical'").copy()
    risk = []
    for i, method in enumerate(VOLATILITY_METHODS):
        f = prototype.copy()
        f["method"] = method
        f["var_fraction"] += i * 0.001
        f["es_fraction"] = f.var_fraction * 1.2
        f["parameter_fit_end"] = "2018-12-31"
        f["regime"] = "low prior volatility"
        for name in ("var", "es", "loss"):
            f[f"{name}_usd"] = f[f"{name}_fraction"] * 1e7
        risk.append(f)
    tables["volatility_forecasts"] = pd.concat(risk, ignore_index=True)
    tables["volatility_fits"] = pd.DataFrame({"strategy": list(STRATEGIES), "status": "ok"})
    dates = prototype.forecast_date.unique()
    tables["correlations"] = pd.DataFrame(
        [
            {"forecast_date": d, "asset_1": "SPY", "asset_2": t, "correlation": 0.2}
            for d in dates
            for t in ("AGG", "GLD", "XLK")
        ]
    )
    tables["robustness_weights"] = pd.DataFrame(
        [
            {
                "strategy": s,
                "variant": v,
                "kind": "prespecified" if v == "full" else "block_resample",
                "status": "ok",
                "one_way_weight_distance": 0.01,
                **dict(zip(UNIVERSE, [0.4, 0, 0, 0.6, 0, 0, 0])),
            }
            for s in ("minimum_volatility", "maximum_sharpe")
            for v in ("full", "block_0", "block_1")
        ]
    )
    tables["income_ledger"] = pd.DataFrame(
        {
            "strategy": ["baseline_40_60"],
            "ex_date": ["2022-01-04"],
            "fixed_notional_distribution_proxy_usd": [1000.0],
        }
    )
    tables["liquidity"] = pd.DataFrame(
        [
            {"strategy": s, "period": p, "participation_proxy": 0.01}
            for s in RESEARCH_PORTFOLIOS
            for p in ("validation", "evaluation")
        ]
    )
    tables["availability"] = pd.DataFrame(
        {"Topic": ["Research limits"], "Status": ["Pending human review"]}
    )
    summary = {
        "snapshot_id": "test",
        "config": asdict(ResearchConfig(spending_months=12)),
        "portfolio_config": bundle.metadata["portfolio"]["config"],
        "backtest_config": bundle.metadata["backtest"]["config"]["backtest"],
        "design_status": "Retrospective test fixture",
        "sources": ["https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf"],
        "spending_source_start": "2022-02",
        "spending_source_end": "2026-09",
        "spending_source_months": 54,
        "spending_limit": "Conditional only",
        "income_limit": "Proxy only",
        "cost_limit": "Assumptions only",
    }
    (root / "uv.lock").write_text("test lock")
    (root / "extra.csv").write_text("test source")
    folder = publish_research(
        root, "test", path, tables, summary, {"extra.csv": file_hash(root / "extra.csv")}
    )
    return root, bundle, folder


def test_research_loads_matching_verified_bundle(research):
    root, bundle, _ = research
    before = file_hash(bundle.manifest_path)
    result = load_research(root, bundle)
    assert len(result.tables["candidate_metrics"]) == 10
    assert len(result.tables["spending_summary"]) == 18
    assert file_hash(bundle.manifest_path) == before


def test_research_is_a_separate_sidebar_page(research):
    root, _, _ = research
    app = app_test(root)
    assert not app.exception
    assert "Research lab" in app.radio(key="page").options
    assert not any(heading.value == "Research lab" for heading in app.header)
    assert len(app.get("bidi_component")) == 1  # Portfolio's own section navigation.

    app.radio(key="page").set_value("Research lab").run()
    assert not app.exception
    assert any(heading.value == "Research lab" for heading in app.header)
    assert app.selectbox(key="lab_topic").value == "Alternative allocations"
    assert len(app.get("bidi_component")) == 0
    app.selectbox(key="lab_topic").set_value("Implementation costs").run()
    assert not app.exception
    app.radio(key="page").set_value("Portfolio").run()
    assert not app.exception
    assert len(app.get("bidi_component")) == 1
    assert all(heading.value != "Research lab" for heading in app.header)


@pytest.mark.parametrize("failure", ["tamper", "source", "stale", "missing", "failed"])
def test_research_refuses_stale_or_tampered_evidence(research, failure):
    root, bundle, folder = research
    if failure == "tamper":
        (folder / "allocation_weights.csv").write_text("changed")
    elif failure == "source":
        (root / "extra.csv").write_text("changed input")
    elif failure == "missing":
        (folder / "spending_summary.csv").unlink()
    else:
        path = folder / "manifest.json"
        manifest = json.loads(path.read_text())
        if failure == "stale":
            manifest["source_bundle_sha256"] = "old"
        else:
            manifest["status"] = "failed"
        write_json(path, manifest)
    with pytest.raises(DashboardDataError):
        load_research(root, bundle)


def test_invalid_published_frequencies_are_unavailable(research):
    root, bundle, folder = research
    path = folder / "spending_summary.csv"
    frame = pd.read_csv(path, float_precision="round_trip")
    frame.loc[0, "no_shortfall_fraction"] = 2
    frame.to_csv(path, index=False)
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["files"][path.name] = file_hash(path)
    write_json(folder / "manifest.json", manifest)
    with pytest.raises(DashboardDataError, match="frequency"):
        load_research(root, bundle)


def test_research_controls_change_actual_tables_and_recalculate_dated_tests(research):
    root, bundle, _ = research
    evidence = load_research(root, bundle)

    def script(evidence, forecasts):
        from saifa.dashboard.research import render_research

        render_research(evidence, forecasts)

    app = AppTest.from_function(
        script, args=(evidence, bundle.tables["backtest"]["forecasts"])
    ).run(timeout=20)
    assert not app.exception
    initial = app.dataframe[1].value.copy()  # Scope table is first.
    app.selectbox(key="lab_allocation_period").set_value("validation").run()
    assert not app.exception and not app.dataframe[1].value.equals(initial)
    app.selectbox(key="lab_topic").set_value("Allocation robustness").run()
    assert not app.exception
    app.selectbox(key="lab_topic").set_value("Volatility and dependence").run()
    assert not app.exception
    observations = app.dataframe[1].value.coverage_observations.iloc[0]
    app.date_input(key="lab_vol_dates").set_value(
        (pd.Timestamp("2022-01-03").date(), pd.Timestamp("2022-01-31").date())
    ).run()
    assert not app.exception
    assert app.dataframe[1].value.coverage_observations.iloc[0] < observations
    app.selectbox(key="lab_vol_method").set_value("historical").run()
    assert not app.exception
    app.selectbox(key="lab_topic").set_value("Spending sustainability").run()
    assert not app.exception
    wealth = app.metric[1].value
    app.selectbox(key="lab_spending_rate").set_value(0.04).run()
    assert not app.exception and app.metric[1].value != wealth
    app.selectbox(key="lab_topic").set_value("Distribution income").run()
    assert not app.exception
    app.selectbox(key="lab_income").set_value("minimum_es").run()
    assert not app.exception and any("review" in w.value for w in app.warning)
    app.selectbox(key="lab_topic").set_value("Implementation costs").run()
    assert not app.exception
    before = app.dataframe[1].value.copy()
    app.selectbox(key="lab_admin_fee").set_value(50.0).run()
    assert not app.exception and not app.dataframe[1].value.equals(before)
