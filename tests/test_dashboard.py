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
from saifa.dashboard.selections import (
    backtest_comparison,
    backtest_view,
    frontier_display_data,
    recent_return_correlations,
    select_risk,
)
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
                            "warning": "Confidence below effective threshold due to ties"
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
                        warning="Confidence below effective threshold due to ties"
                        if unavailable
                        else "Sample warning",
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
                "development_volatility": 0.105 + n * 0.015,
                "development_expected_return": 0.055 + n * 0.005,
                "solver_success": True,
                **{f"weight_{t}": weights.set_index("strategy").loc[s, t] for t in UNIVERSE},
            }
            for n, s in enumerate(list(STRATEGIES)[1:])
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
        {"volatility": [0.1, 0.2], "expected_return": [0.05, 0.09]}
    )
    sample_dates = pd.bdate_range(end="2022-12-30", periods=252)
    sample_days = np.arange(len(sample_dates))
    tables["data"]["simple_returns"] = pd.DataFrame(
        {
            "Date": sample_dates.strftime("%Y-%m-%d"),
            **{ticker: 0.001 * np.sin(sample_days / (n + 3)) for n, ticker in enumerate(UNIVERSE)},
        }
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
                        effective_tail_observations=(1 - confidence) * 1000
                        if method == "historical"
                        else np.nan,
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


def test_model_comparison_recalculates_from_selected_forecast_dates(forecasts):
    config = replace(BacktestConfig(), start="2021-11-01", end_exclusive="2023-01-01")

    def compare(end, confidence=0.99):
        return backtest_comparison(
            forecasts,
            confidence,
            "2022-01-01",
            end,
            config,
            "2022-01-01",
            ("evaluation",),
        )

    full = compare("2022-12-30")
    short = compare("2022-03-31")
    assert len(full) == len(STRATEGIES) * len(METHODS) * 2
    chosen = full.loc[
        (full.Portfolio == "40/60 baseline")
        & (full.Method == "Historical")
        & (full.Check == "Kupiec")
    ].iloc[0]
    assert chosen.Sessions == selected(forecasts).tests.coverage_observations.iloc[0]
    assert chosen["p-value"] == selected(forecasts).tests.coverage_p_value.iloc[0]
    assert (
        short.loc[
            (short.Portfolio == "40/60 baseline")
            & (short.Method == "Historical")
            & (short.Check == "Kupiec"),
            "Sessions",
        ].iloc[0]
        < chosen.Sessions
    )
    unavailable = compare("2022-12-30", 0.90)
    evt = unavailable.loc[unavailable.Method == "EVT · POT/GPD"]
    assert set(evt.Decision) == {"unavailable"}
    assert (evt["Missing forecasts"] > 0).all()


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
    # Deliberate tied/failed-tail fixture: genuine missing results must remain missing.
    view = selected(forecasts, confidence=0.9, method="evt_pot_gpd")
    assert view.forecasts.exception.isna().all()
    assert view.tests.coverage_decision.iloc[0] == "unavailable"
    assert view.lights.status.iloc[0] == "unsupported_confidence"


def test_available_boundary_controls_and_date_range_recalculation(prepared):
    root, _, outputs = prepared
    path = outputs["risk"] / "risk_comparison.csv"
    risk = pd.read_csv(path)
    selected_rows = risk.method.eq("evt_pot_gpd") & risk.confidence.eq(0.9)
    for column, value in {
        "var_fraction": 0.01,
        "es_fraction": 0.015,
        "var_usd": 100000,
        "es_usd": 150000,
        "var_percent": 1,
        "es_percent": 1.5,
        "status": "ok",
        "warning": "Threshold-boundary estimate: empirical VaR; fitted ES",
        "interval_warning": "Intervals withheld: >10% invalid VaR draws",
        "var_valid_replicates": 124,
        "es_valid_replicates": 124,
    }.items():
        risk.loc[selected_rows, column] = value
    risk.to_csv(path, index=False)
    path = outputs["backtest"] / "forecasts.csv"
    forecasts = pd.read_csv(path)
    selected_rows = forecasts.method.eq("evt_pot_gpd") & forecasts.confidence.eq(0.9)
    forecasts.loc[selected_rows, "var_fraction"] = 0.01
    forecasts.loc[selected_rows, "var_usd"] = 100000
    forecasts.loc[selected_rows, "exception"] = (
        forecasts.loc[selected_rows, "loss_fraction"] > 0.01
    ).astype(int)
    forecasts.loc[selected_rows, "status"] = "ok"
    forecasts.loc[selected_rows, "warning"] = "Threshold-boundary estimate"
    forecasts.to_csv(path, index=False)
    publish_bundle(root, root / "data/snapshots/test", outputs)

    full = selected(forecasts, confidence=0.9, method="evt_pot_gpd")
    short = selected(forecasts, end="2022-03-31", confidence=0.9, method="evt_pot_gpd")
    assert full.tests.coverage_missing_forecasts.iloc[0] == 0
    assert full.tests.coverage_observations.iloc[0] > short.tests.coverage_observations.iloc[0]
    assert full.tests.coverage_p_value.iloc[0] != short.tests.coverage_p_value.iloc[0]
    assert full.lights.status.iloc[0] == "unsupported_confidence"  # Basel remains 99% only.
    app = app_test(root)
    app.radio(key="page").set_value("Risk comparison").run()
    app.selectbox(key="method").set_value("evt_pot_gpd").run()
    app.selectbox(key="confidence").set_value(0.9).run()
    assert not app.exception
    assert app.metric[0].value == "$100,000.00"
    assert app.metric[2].value == "$150,000.00"
    assert any("threshold boundary" in c.value for c in app.caption)
    assert any("Intervals withheld" in w.value for w in app.warning)
    assert not any("90% is unavailable" in w.value for w in app.warning)
    app.selectbox(key="confidence").set_value(0.95).run()
    assert app.metric[0].value != "$100,000.00"
    app.selectbox(key="confidence").set_value(0.9).run()
    app.radio(key="page").set_value("Backtesting").run()
    assert not app.exception
    assert app.metric[0].value != "Unavailable"
    observations = app.metric[2].value
    app.date_input(key="dates").set_value(
        (pd.Timestamp("2022-01-01").date(), pd.Timestamp("2022-03-31").date())
    ).run()
    assert not app.exception
    assert app.metric[2].value != observations


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


def test_stress_historical_es_sparse_tail_warning_is_visible(prepared):
    root, _, _ = prepared
    app = app_test(root)
    app.radio(key="page").set_value("Stress analysis").run()
    assert not app.exception
    assert any("Only 10 effective worst-tail observations" in w.value for w in app.warning)

    app.selectbox(key="confidence").set_value(0.95).run()
    assert not any("effective worst-tail observations" in w.value for w in app.warning)

    app.selectbox(key="confidence").set_value(0.99).run()
    app.selectbox(key="method").set_value("parametric_normal").run()
    assert not any("effective worst-tail observations" in w.value for w in app.warning)


def test_backtest_chart_zooms_and_lists_exact_exception_dates(prepared):
    root, _, outputs = prepared
    forecasts = pd.read_csv(outputs["backtest"] / "forecasts.csv")
    app = app_test(root)
    app.radio(key="page").set_value("Backtesting").run()
    assert not app.exception

    chart = json.loads(app.get("vega_lite_chart")[-1].proto.spec)
    assert chart["params"][0]["bind"] == "scales"
    assert chart["params"][0]["select"]["encodings"] == ["x"]
    tooltip_fields = {item["field"] for item in chart["layer"][-1]["encoding"]["tooltip"]}
    assert tooltip_fields == {"forecast_date", "var_usd", "loss_usd", "excess_usd"}

    def exception_table():
        return next(
            frame.value for frame in app.dataframe if "Above VaR (USD)" in frame.value.columns
        )

    full = exception_table()
    assert len(full) == int(selected(forecasts).forecasts.exception.sum())
    assert (full["Above VaR (USD)"] > 0).all()
    app.date_input(key="dates").set_value(
        (pd.Timestamp("2022-01-01").date(), pd.Timestamp("2022-03-31").date())
    ).run()
    assert not app.exception
    short = exception_table()
    assert len(short) == int(selected(forecasts, end="2022-03-31").forecasts.exception.sum())
    assert len(short) < len(full)


def test_backtest_period_buttons_sync_with_sidebar_and_restore_custom_dates(prepared):
    root, _, _ = prepared
    app = app_test(root)
    app.radio(key="page").set_value("Backtesting").run()
    assert not app.exception
    assert app.date_input(key="dates").value == (
        pd.Timestamp("2022-01-01").date(),
        pd.Timestamp("2022-12-30").date(),
    )
    evaluation_sessions = app.metric[2].value

    app.button(key="backtest_period_validation").click().run()
    assert not app.exception
    assert app.date_input(key="dates").value == (
        pd.Timestamp("2021-11-01").date(),
        pd.Timestamp("2021-12-31").date(),
    )
    assert app.metric[2].value != evaluation_sessions
    assert any(heading.value.startswith("Validation ·") for heading in app.subheader)

    app.button(key="backtest_period_all_forecasts").click().run()
    assert not app.exception
    assert app.date_input(key="dates").value == (
        pd.Timestamp("2021-11-01").date(),
        pd.Timestamp("2022-12-30").date(),
    )
    assert any(heading.value.startswith("Evaluation ·") for heading in app.subheader)

    app.date_input(key="dates").set_value(
        (pd.Timestamp("2022-01-01").date(), pd.Timestamp("2022-03-31").date())
    ).run()
    assert not app.exception
    assert any("Showing 2022-01-01 to 2022-03-31" in c.value for c in app.caption)
    app.button(key="backtest_period_evaluation").click().run()
    assert not app.exception
    assert app.date_input(key="dates").value == (
        pd.Timestamp("2022-01-01").date(),
        pd.Timestamp("2022-12-30").date(),
    )
    assert app.metric[2].value == evaluation_sessions

    app.date_input(key="dates").set_value((pd.Timestamp("2022-03-01").date(),)).run()
    assert not app.exception
    assert any("Select both a start and an end date" in message.value for message in app.info)
    app.button(key="backtest_period_evaluation").click().run()
    assert not app.exception
    assert app.metric[2].value == evaluation_sessions


def test_portfolio_section_links_match_rendered_anchors_across_reruns(prepared):
    root, _, _ = prepared
    app = app_test(root)
    assert not app.exception
    expected = [
        "portfolio-summary",
        "portfolio-performance",
        "portfolio-drawdown",
        "portfolio-frontier",
        "portfolio-diversification",
        "portfolio-spending",
    ]

    def rendered_ids():
        component = app.get("bidi_component")[0].proto
        configuration = json.loads(component.json)
        links = [entry["id"] for entry in configuration["sections"]]
        assert configuration["pinned_id"] == "portfolio-summary"
        page_heading = next(
            heading for heading in app.header if heading.value == "Portfolio performance"
        )
        assert page_heading.proto.anchor == "portfolio-page"
        assert page_heading.proto.anchor not in links
        assert component.html_content.index('class="nav-pinned"') < component.html_content.index(
            'class="nav-links"'
        )
        headings = [
            (heading.proto.anchor, heading.value)
            for heading in app.subheader
            if heading.proto.anchor in expected
        ]
        return links, headings

    expected_headings = [
        ("portfolio-summary", "Selected portfolio at a glance"),
        ("portfolio-performance", "Performance and holdings"),
        ("portfolio-drawdown", "Drawdown · 40/60 baseline"),
        ("portfolio-frontier", "Development-period efficient frontier"),
        ("portfolio-diversification", "How do the seven ETFs move together?"),
        ("portfolio-spending", "Purchasing power and spending"),
    ]
    assert rendered_ids() == (expected, expected_headings)
    headings = [item.value for item in app.subheader]
    assert "Selected portfolio at a glance" in headings
    assert "Performance and holdings" in headings
    assert any(value.startswith("Drawdown ·") for value in headings)
    assert "Development-period efficient frontier" in headings
    assert "How do the seven ETFs move together?" in headings
    app.selectbox(key="strategy").set_value("maximum_sharpe").run()
    assert not app.exception
    assert [anchor for anchor, _ in rendered_ids()[1]] == expected
    app.radio(key="page").set_value("Risk comparison").run()
    assert not app.exception
    assert len(app.get("bidi_component")) == 1


def test_analysis_page_section_navigation_tracks_visible_sections(prepared):
    root, _, _ = prepared
    app = app_test(root)

    def check_page(page, expected_ids, heading_anchor, aria_label):
        app.radio(key="page").set_value(page).run()
        assert not app.exception
        component = app.get("bidi_component")[0].proto
        configuration = json.loads(component.json)
        ids = [section["id"] for section in configuration["sections"]]
        assert ids == expected_ids
        assert configuration["pinned_id"] == expected_ids[0]
        assert configuration["aria_label"] == aria_label
        assert heading_anchor not in ids
        assert heading_anchor in {heading.proto.anchor for heading in app.header}
        anchored = [
            heading.proto.anchor
            for heading in app.subheader
            if heading.proto.anchor in expected_ids
        ]
        assert anchored == expected_ids

    check_page(
        "Risk comparison",
        ["risk-portfolios", "risk-selected", "risk-methods"],
        "risk-page",
        "Risk comparison sections",
    )
    app.selectbox(key="method").set_value("parametric_normal").run()
    assert not app.exception
    assert any(heading.proto.anchor == "risk-selected" for heading in app.subheader)

    check_page(
        "Backtesting",
        ["backtest-overview", "backtest-evaluation", "backtest-models", "backtest-forecasts"],
        "backtest-page",
        "Backtesting sections",
    )
    app.date_input(key="dates").set_value(
        (pd.Timestamp("2021-12-30").date(), pd.Timestamp("2022-01-07").date())
    ).run()
    assert not app.exception
    configuration = json.loads(app.get("bidi_component")[0].proto.json)
    assert [section["id"] for section in configuration["sections"]] == [
        "backtest-overview",
        "backtest-validation",
        "backtest-evaluation",
        "backtest-models",
        "backtest-forecasts",
    ]
    check_page(
        "Stress analysis",
        ["stress-crisis", "stress-compare", "stress-shock", "stress-contributions"],
        "stress-page",
        "Stress analysis sections",
    )
    app.select_slider(key="severity").set_value(1.5).run()
    assert not app.exception
    assert len(app.get("bidi_component")) == 1
    app.radio(key="page").set_value("Assumptions").run()
    assert not app.exception
    assert not app.get("bidi_component")


def test_frontier_display_uses_saved_development_estimates(prepared):
    root, path, _ = prepared
    bundle = load_bundle(root, path)
    curve, points = frontier_display_data(
        bundle.tables["portfolio"]["efficient_frontier"],
        bundle.tables["portfolio"]["candidate_weights"],
    )
    assert curve["Annual volatility (%)"].tolist() == pytest.approx([10.0, 20.0])
    assert points["Annual volatility (%)"].tolist() == pytest.approx([10.5, 12.0])
    assert points["Expected annual return (%)"].tolist() == pytest.approx([5.5, 6.0])
    assert points.Portfolio.tolist() == ["Minimum volatility", "Maximum Sharpe"]
    app = app_test(root)
    assert not app.exception
    assert any("Development-period efficient frontier" in item.value for item in app.subheader)
    assert not any("Efficient frontier unavailable" in item.value for item in app.warning)


def test_frontier_display_rejects_unavailable_candidate_estimate(prepared):
    root, path, _ = prepared
    bundle = load_bundle(root, path)
    candidates = bundle.tables["portfolio"]["candidate_weights"].copy()
    candidates.loc[0, "development_expected_return"] = np.nan
    with pytest.raises(DashboardDataError, match="unavailable"):
        frontier_display_data(bundle.tables["portfolio"]["efficient_frontier"], candidates)


def test_recent_return_correlations_use_aligned_returns():
    values = np.array([0.01, -0.02, 0.03, -0.04])
    frame = pd.DataFrame(
        {
            "Date": pd.date_range("2022-01-03", periods=4).strftime("%Y-%m-%d"),
            **{ticker: np.roll(values, n) for n, ticker in enumerate(UNIVERSE)},
        }
    )
    frame["XLK"] = 2 * values
    frame["AGG"] = -values
    matrix, first, last = recent_return_correlations(frame, sessions=4)
    assert (str(first.date()), str(last.date())) == ("2022-01-03", "2022-01-06")
    assert matrix.loc["SPY", "XLK"] == pytest.approx(1)
    assert matrix.loc["SPY", "AGG"] == pytest.approx(-1)
    assert np.allclose(matrix.to_numpy(), matrix.to_numpy().T)
    assert np.allclose(np.diag(matrix), 1)


def test_recent_return_correlations_do_not_hide_missing_returns():
    frame = pd.DataFrame({"Date": ["2022-01-03", "2022-01-04"], **dict.fromkeys(UNIVERSE, 0.01)})
    frame.loc[1, "SPY"] = np.nan
    with pytest.raises(DashboardDataError, match="missing or invalid"):
        recent_return_correlations(frame, sessions=2)


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


def test_bundle_rejects_changed_correlation_source(prepared):
    root, path, outputs = prepared
    (outputs["data"] / "simple_returns.csv").write_text("changed\n")
    with pytest.raises(DashboardDataError, match="simple_returns.csv changed"):
        verify_bundle(root, path)


def test_source_snapshot_tampering_is_reported(prepared):
    root, path, _ = prepared
    (root / "data/snapshots/test/SPY.csv").write_text("changed\n")
    with pytest.raises(DashboardDataError, match="Snapshot input changed"):
        verify_bundle(root, path)
