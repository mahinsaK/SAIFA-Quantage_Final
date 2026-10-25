"""Independent UI selections, calendar-preserving tests and verified bundle loading."""

import json
from dataclasses import asdict, replace

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

from saifa.application.dashboard_pipeline import publish_bundle
from saifa.dashboard.data import load_bundle, verify_bundle
from saifa.dashboard.selections import backtest_view, select_risk
from saifa.data.snapshots import file_hash
from saifa.domain.config import UNIVERSE, BacktestConfig, OptimisationConfig, RiskConfig
from saifa.domain.dashboard import CONFIDENCES, METHODS, STRATEGIES, TABLES, DashboardDataError


def forecasts_fixture():
    dates = xcals.get_calendar("XNYS", start="2021-11-01", end="2022-12-30").sessions.tz_localize(
        None
    )
    records = []
    for s, strategy in enumerate(STRATEGIES):
        for m, method in enumerate(METHODS):
            for confidence in CONFIDENCES:
                for i, date in enumerate(dates):
                    var = (confidence - 0.8) / 10 + m * 0.0003 + s * 0.0002
                    loss = 0.025 if i % (9 + s) == 0 else -0.002
                    unavailable = method == "evt_pot_gpd" and confidence == 0.90
                    records.append(
                        {
                            "strategy": strategy,
                            "method": method,
                            "confidence": confidence,
                            "forecast_date": str(date.date()),
                            "as_of": str((date - pd.Timedelta(days=1)).date()),
                            "period": "validation" if date.year == 2021 else "evaluation",
                            "weights_as_of": "2018-12-31",
                            "reference_nav": 10_000_000,
                            "horizon_sessions": 1,
                            "observations": 1000,
                            "var_fraction": np.nan if unavailable else var,
                            "var_usd": np.nan if unavailable else var * 10_000_000,
                            "loss_fraction": loss,
                            "loss_usd": loss * 10_000_000,
                            "exception": np.nan if unavailable else int(loss > var),
                            "status": "unsupported" if unavailable else "ok",
                            "warning": "Confidence at threshold"
                            if unavailable
                            else "Sample warning",
                        }
                    )
    return pd.DataFrame(records)


@pytest.fixture(scope="module")
def forecasts():
    return forecasts_fixture()


@pytest.fixture
def prepared(tmp_path, forecasts):
    snapshot = tmp_path / "data/snapshots/test"
    snapshot.mkdir(parents=True)
    (tmp_path / "data/LATEST").write_text("test\n")
    raw_files = {}
    for name in [*[f"{t}.csv" for t in UNIVERSE], "fred.csv"]:
        (snapshot / name).write_text("test fixture input\n")
        raw_files[name] = file_hash(snapshot / name)
    (snapshot / "manifest.json").write_text(
        json.dumps({"status": "complete", "snapshot_id": "test", "files": raw_files})
    )
    policy = asdict(OptimisationConfig())
    risk_config = asdict(replace(RiskConfig(), confidence_levels=CONFIDENCES))
    config = replace(
        BacktestConfig(),
        start="2021-11-01",
        end_exclusive="2023-01-01",
        confidence_levels=CONFIDENCES,
    )
    common = {
        "snapshot_id": "test",
        "as_of": "2022-12-30",
        "forecast_session": "2023-01-03",
        "window_start": "2019-01-02",
        "observations": 1000,
        "reference_nav": 10_000_000,
    }
    meta = {
        "portfolio": {"snapshot_id": "test", "config": policy},
        "risk": dict(common, config={"risk": risk_config, "portfolio": policy}),
        "stress": dict(
            common,
            config={"portfolio": policy},
            shock_narrative="Synthetic test scenario; team approval pending.",
        ),
        "backtest": {
            "snapshot_id": "test",
            "start": "2021-11-01",
            "end": "2022-12-30",
            "validation_end_exclusive": "2022-01-01",
            "config": {"portfolio": policy, "backtest": asdict(config)},
        },
        "data": {
            "snapshot_id": "test",
            "first_return": "2004-11-19",
            "last_return": "2022-12-30",
            "returns": 4000,
            "review_flags": 3,
        },
    }
    tables = {stage: {} for stage in TABLES}
    weights = pd.DataFrame(
        [{"strategy": s, **dict.fromkeys(UNIVERSE, 0), "SPY": 0.4, "AGG": 0.6} for s in STRATEGIES]
    )
    riskrows = []
    for n, strategy in enumerate(STRATEGIES):
        for m, method in enumerate(METHODS):
            for confidence in CONFIDENCES:
                var = (confidence - 0.8) / 10 + n * 0.001 + m * 0.0001
                unavailable = method == "evt_pot_gpd" and confidence == 0.9
                var = np.nan if unavailable else var
                riskrows.append(
                    dict(
                        common,
                        strategy=strategy,
                        method=method,
                        confidence=confidence,
                        horizon_sessions=1,
                        var_fraction=var,
                        es_fraction=var * 1.2,
                        var_usd=var * 1e7,
                        es_usd=var * 1.2e7,
                        var_percent=var * 100,
                        es_percent=var * 120,
                        status="unsupported" if unavailable else "ok",
                        warning="Threshold boundary" if unavailable else "Sample warning",
                    )
                )
    tables["risk"] = {
        "risk_comparison": pd.DataFrame(riskrows),
        "portfolio_weights": weights,
        "threshold_diagnostics": pd.DataFrame({"strategy": list(STRATEGIES), "shape": [0.1] * 3}),
        "threshold_sensitivity": pd.DataFrame(
            [
                {"strategy": s, "confidence": c, "quantile": 0.9}
                for s in STRATEGIES
                for c in CONFIDENCES
            ]
        ),
    }
    tables["portfolio"]["candidate_weights"] = pd.DataFrame(
        [
            {
                "strategy": s,
                **{f"weight_{t}": weights.set_index("strategy").loc[s, t] for t in UNIVERSE},
            }
            for s in list(STRATEGIES)[1:]
        ]
    )
    tables["portfolio"]["evaluation_daily"] = pd.DataFrame(
        [
            {
                "strategy": s,
                "Date": date,
                "nav": nav,
                "drawdown": dd,
                **{f"{t}_weight": weights.set_index("strategy").loc[s, t] for t in UNIVERSE},
            }
            for s in STRATEGIES
            for date, nav, dd in [("2022-01-03", 9990010, -0.000999), ("2022-12-30", 11_000_000, 0)]
        ]
    )
    tables["portfolio"]["evaluation_metrics"] = pd.DataFrame(
        [
            {
                "strategy": s,
                "start_date": "2022-01-03",
                "end_date": "2022-12-30",
                "ending_value": 11e6,
                "cumulative_return": 0.1,
                "annualised_return": 0.1,
                "maximum_drawdown": -0.15,
            }
            for s in STRATEGIES
        ]
    )
    tables["portfolio"]["performance_ratios"] = pd.DataFrame(
        {"strategy": list(STRATEGIES), "sharpe_ratio": [1.0, 0.9, 0.8]}
    )
    tables["portfolio"]["efficient_frontier"] = pd.DataFrame(
        {"volatility": [0.1], "expected_return": [0.05]}
    )
    tables["backtest"]["forecasts"] = forecasts
    totals, assets, sizing, histories, paths, shock_summaries, shock_parts = (
        [],
        [],
        [],
        [],
        [],
        [],
        [],
    )
    for strategy in STRATEGIES:
        for confidence in CONFIDENCES:
            for method, measure in [
                ("historical", "es"),
                ("parametric_normal", "var"),
                ("parametric_normal", "es"),
            ]:
                identity = {
                    "strategy": strategy,
                    "confidence": confidence,
                    "method": method,
                    "measure": measure,
                }
                totals.append(
                    dict(
                        identity,
                        total_percent=2,
                        total_usd=200000,
                        status="ok",
                        warning="Sample warning",
                    )
                )
                for ticker in UNIVERSE:
                    assets.append(
                        dict(
                            identity,
                            ticker=ticker,
                            weight=1 / 7,
                            marginal_fraction=0.02,
                            component_percent=2 / 7,
                            component_usd=200000 / 7,
                            share_percent=100 / 7,
                        )
                    )
                sizing.append(
                    dict(
                        identity,
                        donor="SPY",
                        receiver="AGG",
                        feasible=False,
                        reason="Policy",
                        delta_usd=np.nan,
                    )
                )
        histories.append(
            {
                "strategy": strategy,
                "scenario": "2008_GFC",
                "requested_start": "2008-01-01",
                "requested_end_exclusive": "2009-01-01",
                "observed_sessions": 253,
                "expected_sessions": 253,
                "status": "ok",
                "warning": "Retrospective",
                "terminal_loss_usd": 1e6,
                "maximum_drawdown_fraction": 0.2,
                "drawdown_usd_at_max_fraction": 2e6,
                "drawdown_review_level": 0.15,
                "peak_nav": 1e7,
                "trough_nav": 8e6,
                "peak_date": "2007-12-31",
                "trough_date": "2008-10-01",
            }
        )
        paths.extend(
            [
                {
                    "strategy": strategy,
                    "scenario": "2008_GFC",
                    "Date": date,
                    "nav": nav,
                    "drawdown_fraction": dd,
                }
                for date, nav, dd in [("2007-12-31", 1e7, 0), ("2008-10-01", 8e6, 0.2)]
            ]
        )
        for multiplier in (0.5, 1, 1.5):
            shock_summaries.append(
                {
                    "strategy": strategy,
                    "multiplier": multiplier,
                    "loss_fraction": 0.084 * multiplier,
                    "loss_usd": 840000 * multiplier,
                    "review_level": 0.1,
                }
            )
            shock_parts.extend(
                [
                    {
                        "strategy": strategy,
                        "multiplier": multiplier,
                        "ticker": t,
                        "loss_usd": 120000 * multiplier,
                    }
                    for t in UNIVERSE
                ]
            )
    tables["stress"] = {
        "portfolio_weights": weights,
        "contribution_summary": pd.DataFrame(totals),
        "asset_contributions": pd.DataFrame(assets),
        "sizing_checks": pd.DataFrame(sizing),
        "historical_summary": pd.DataFrame(histories),
        "historical_paths": pd.DataFrame(paths),
        "hypothetical_summary": pd.DataFrame(shock_summaries),
        "hypothetical_components": pd.DataFrame(shock_parts),
        "scenario_shocks": pd.DataFrame({"ticker": UNIVERSE, "base_shock_return": [-0.12] * 7}),
    }
    outputs = {}
    for stage in TABLES:
        folder = tmp_path / "output" / stage
        folder.mkdir(parents=True)
        outputs[stage] = folder
        (folder / "status.json").write_text(
            json.dumps({"snapshot_id": "test", "status": "complete"})
        )
        (folder / "summary.json").write_text(json.dumps(meta[stage]))
        for name, frame in tables[stage].items():
            frame.to_csv(folder / f"{name}.csv", index=False)
    path = publish_bundle(tmp_path, snapshot, outputs)
    return tmp_path, path, outputs


def test_bundle_loads_and_hash_verification_catches_mutation(prepared):
    root, path, outputs = prepared
    bundle = load_bundle(root, path)
    assert len(bundle.tables["risk"]["risk_comparison"]) == 36
    (outputs["risk"] / "risk_comparison.csv").write_text("corrupt\n")
    with pytest.raises(DashboardDataError, match="changed"):
        verify_bundle(root, path)


@pytest.mark.parametrize("problem", ["missing", "building", "snapshot", "escape"])
def test_bundle_rejects_missing_partial_mixed_and_external_inputs(prepared, problem):
    root, path, outputs = prepared
    manifest = json.loads(path.read_text())
    if problem == "missing":
        (outputs["backtest"] / "forecasts.csv").unlink()
    elif problem == "building":
        manifest["status"] = "building"
    elif problem == "snapshot":
        manifest["snapshot_id"] = "wrong"
    else:
        manifest["stages"]["risk"]["path"] = "../outside"
    path.write_text(json.dumps(manifest))
    with pytest.raises(DashboardDataError):
        load_bundle(root, path)


def test_changed_confidence_and_portfolio_select_real_rows(prepared):
    root, path, _ = prepared
    frame = load_bundle(root, path).tables["risk"]["risk_comparison"]
    a = select_risk(frame, "baseline_40_60", 0.95).set_index("method")
    b = select_risk(frame, "baseline_40_60", 0.99).set_index("method")
    c = select_risk(frame, "maximum_sharpe", 0.99).set_index("method")
    assert (
        a.loc["historical", "var_usd"]
        < b.loc["historical", "var_usd"]
        < c.loc["historical", "var_usd"]
    )
    unsupported = select_risk(frame, "baseline_40_60", 0.9).set_index("method").loc["evt_pot_gpd"]
    assert np.isnan(unsupported.var_usd) and unsupported.status == "unsupported"


def selected(forecasts, start="2022-01-01", end="2022-12-30", confidence=0.99, method="historical"):
    return backtest_view(
        forecasts,
        "baseline_40_60",
        method,
        confidence,
        start,
        end,
        replace(BacktestConfig(), start="2021-11-01", end_exclusive="2023-01-01"),
        "2022-01-01",
    )


def test_date_selection_recalculates_counts_and_resets_basel(forecasts):
    full = selected(forecasts)
    short = selected(forecasts, end="2022-03-31")
    assert full.tests.coverage_observations.iloc[0] == 251
    assert short.tests.coverage_observations.iloc[0] == 62
    assert full.tests.coverage_exceptions.iloc[0] > short.tests.coverage_exceptions.iloc[0]
    assert full.tests.coverage_p_value.iloc[0] != short.tests.coverage_p_value.iloc[0]
    assert full.lights.status.iloc[0] == "ok"
    assert short.lights.status.iloc[0] == "insufficient_window"
    cross = selected(forecasts, start="2021-12-01", end="2022-03-31")
    assert cross.tests.period.tolist() == ["validation", "evaluation"]
    assert (cross.lights.status == "insufficient_window").all()


def test_missing_day_is_retained_and_equality_is_not_exception(forecasts):
    f = forecasts.copy()
    match = (
        (f.strategy == "baseline_40_60")
        & (f.method == "historical")
        & (f.confidence == 0.99)
        & (f.forecast_date == "2022-01-04")
    )
    f.loc[match, "loss_fraction"] = f.loc[match, "var_fraction"]
    equal = selected(f, start="2022-01-04", end="2022-01-04")
    assert equal.forecasts.exception.iloc[0] == 0
    f = f.loc[~match]
    missing = selected(f, start="2022-01-03", end="2022-01-07")
    assert len(missing.forecasts) == 5
    assert missing.tests.coverage_missing_forecasts.iloc[0] == 1
    assert missing.tests.coverage_decision.iloc[0] == "unavailable"
    assert missing.tests.independence_decision.iloc[0] == "unavailable"


def test_90pct_evt_unavailable_without_replacing_forecasts(forecasts):
    view = selected(forecasts, confidence=0.9, method="evt_pot_gpd")
    assert view.forecasts.exception.isna().all()
    assert view.tests.coverage_decision.iloc[0] == "unavailable"
    assert view.lights.status.iloc[0] == "unsupported_confidence"


@pytest.mark.parametrize(
    "start,end",
    [
        ("2022-03-01", "2022-02-01"),
        ("2021-10-01", "2022-01-01"),
        ("2022-01-01", "2023-01-02"),
        ("2022-01-08", "2022-01-09"),
    ],
)
def test_invalid_or_no_session_dates_explained(forecasts, start, end):
    with pytest.raises(DashboardDataError):
        selected(forecasts, start, end)


def app_test(root):
    return AppTest.from_string(
        f"from pathlib import Path\nfrom app import main\nmain(Path({str(root)!r}))",
        default_timeout=15,
    ).run()


def test_app_missing_bundle_is_actionable_and_does_not_download(tmp_path, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr("requests.sessions.Session.request", no_network)
    app = app_test(tmp_path)
    assert not app.exception
    assert "not ready" in app.error[0].value
    assert "commands/run_app_data.py" in app.code[0].value


def test_app_controls_pages_and_unavailable_results(prepared, monkeypatch):
    def no_network(*args, **kwargs):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr("requests.sessions.Session.request", no_network)
    root, _, _ = prepared
    app = app_test(root)
    assert not app.exception
    app.radio(key="page").set_value("Risk comparison").run()
    base = app.metric[0].value
    app.selectbox(key="confidence").set_value(0.95).run()
    assert app.metric[0].value != base
    assert app.metric[0].value == "$150,000.00"
    app.selectbox(key="strategy").set_value("maximum_sharpe").run()
    assert app.metric[0].value == "$170,000.00"
    app.selectbox(key="method").set_value("parametric_normal").run()
    normal = app.metric[0].value
    assert normal == "$171,000.00"
    app.selectbox(key="method").set_value("evt_pot_gpd").run()
    app.selectbox(key="confidence").set_value(0.9).run()
    assert app.metric[0].value == "Unavailable"
    assert any("threshold" in x.value.lower() for x in app.warning)
    assert normal != "Unavailable"
    app.radio(key="page").set_value("Backtesting").run()
    assert not app.exception
    assert app.metric[0].value == "Unavailable"
    app.selectbox(key="method").set_value("historical").run()
    app.selectbox(key="confidence").set_value(0.99).run()
    full = app.metric[2].value
    app.date_input(key="dates").set_value(
        (pd.Timestamp("2022-01-01").date(), pd.Timestamp("2022-03-31").date())
    ).run()
    assert app.metric[2].value != full
    app.radio(key="page").set_value("Stress analysis").run()
    assert not app.exception
    assert any("2018" in x.value for x in app.warning)
    base = app.metric[-1].value
    app.select_slider(key="severity").set_value(1.5).run()
    assert app.metric[-1].value != base
    app.radio(key="page").set_value("Assumptions").run()
    assert not app.exception


def test_bundle_rejects_inconsistent_units_even_with_updated_hash(prepared):
    root, path, outputs = prepared
    csv = outputs["risk"] / "risk_comparison.csv"
    frame = pd.read_csv(csv)
    frame.loc[0, "var_usd"] *= 100
    frame.to_csv(csv, index=False)
    manifest = json.loads(path.read_text())
    manifest["stages"]["risk"]["files"]["risk_comparison.csv"] = file_hash(csv)
    path.write_text(json.dumps(manifest))
    with pytest.raises(DashboardDataError, match="units"):
        load_bundle(root, path)


def test_stage_status_is_checked_independently_of_bundle_status(prepared):
    root, path, outputs = prepared
    status = outputs["risk"] / "status.json"
    status.write_text(json.dumps({"snapshot_id": "test", "status": "failed"}))
    manifest = json.loads(path.read_text())
    manifest["stages"]["risk"]["files"]["status.json"] = file_hash(status)
    path.write_text(json.dumps(manifest))
    with pytest.raises(DashboardDataError, match="not complete"):
        load_bundle(root, path)


def test_cache_cannot_hide_a_changed_output(prepared):
    root, _, outputs = prepared
    app = app_test(root)
    assert not app.exception and app.metric
    (outputs["risk"] / "risk_comparison.csv").write_text("changed\n")
    app.run()
    assert not app.exception
    assert "not ready" in app.error[0].value
    assert not app.metric


def test_source_snapshot_tampering_is_reported(prepared):
    root, path, _ = prepared
    (root / "data/snapshots/test/SPY.csv").write_text("changed\n")
    with pytest.raises(DashboardDataError, match="Snapshot input changed"):
        verify_bundle(root, path)
