"""Offline annual experiment publication, provenance and real UI controls."""

import json

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from test_dashboard import forecasts as forecasts  # noqa: PLC0414 - fixture export
from test_dashboard import prepared as prepared  # noqa: PLC0414 - fixture export

from saifa.application.adaptive_pipeline import build_adaptive
from saifa.application.dashboard_pipeline import publish_bundle
from saifa.application.optimisation_pipeline import _month_ends
from saifa.dashboard.adaptive import load_adaptive
from saifa.dashboard.data import load_bundle
from saifa.data.snapshots import file_hash, write_json
from saifa.domain.config import UNIVERSE
from saifa.domain.dashboard import DashboardDataError
from saifa.models.portfolio import simulate_portfolio


@pytest.fixture
def experiment(prepared):
    root, path, outputs = prepared
    dates = xcals.get_calendar("XNYS", start="2013-01-01", end="2022-12-31").sessions.tz_localize(
        None
    )
    rng = np.random.default_rng(73)
    changes = rng.normal(0.0003, 0.01, (len(dates), len(UNIVERSE)))
    changes[:, 3] = rng.normal(0.0001, 0.003, len(dates))
    prices = pd.DataFrame(100 * np.cumprod(1 + changes, axis=0), index=dates, columns=UNIVERSE)
    returns = prices.pct_change().iloc[1:]
    data = outputs["data"]
    prices.to_csv(data / "adjusted_prices.csv", index_label="Date", float_format="%.17g")
    returns.to_csv(data / "simple_returns.csv", index_label="Date", float_format="%.17g")
    pd.DataFrame({"simple_return": 0.00005}, index=dates).to_csv(
        data / "risk_free_returns.csv", index_label="Date", float_format="%.17g"
    )
    for stage in ("portfolio", "risk", "stress", "backtest"):
        summary = json.loads((outputs[stage] / "summary.json").read_text())
        policy = summary["config"] if stage == "portfolio" else summary["config"]["portfolio"]
        policy["evaluation_end_exclusive"] = "2023-01-01"
        write_json(outputs[stage] / "summary.json", summary)
    summary = json.loads((data / "summary.json").read_text())
    summary["config"] = {"calendar": "XNYS"}
    summary["outputs_sha256"] = {p.name: file_hash(p) for p in data.glob("*.csv")}
    write_json(data / "summary.json", summary)
    (root / "uv.lock").write_text("test-only lock input")
    (root / "src/saifa").mkdir(parents=True)
    (root / "src/saifa/example.py").write_text("# test-only source provenance")
    publish_bundle(root, root / "data/snapshots/test", outputs)
    digest = file_hash(path)
    folder = build_adaptive(root, root / "data/snapshots/test")
    return root, path, folder, digest, prices


def test_pipeline_preserves_base_and_produces_consistent_cash_accounting(experiment):
    root, path, _, digest, prices = experiment
    bundle = load_bundle(root, path)
    evidence = load_adaptive(root, bundle)
    assert file_hash(path) == digest
    assert len(evidence.tables["metrics"]) == 10
    assert len(evidence.tables["annual_targets"]) == 8
    audit = evidence.tables["annual_targets"]
    assert (audit.training_end < audit.execution_date).all()
    tx = evidence.tables["transactions"]
    assert np.allclose(tx.nav_before, tx.nav_after + tx.transaction_cost, atol=1e-7)
    assert np.allclose(tx.gross_traded * 0.001, tx.transaction_cost, atol=1e-7)
    grouped = evidence.tables["daily"].groupby(["period", "strategy"])
    for (period, strategy), rows in grouped:
        metric = (
            evidence.tables["metrics"].query("period == @period and strategy == @strategy").iloc[0]
        )
        assert rows.nav.iloc[-1] == pytest.approx(metric.ending_value)
        assert rows.Date.iloc[0] == metric.start_date
    evaluation = prices.loc["2022"]
    weights = (
        bundle.tables["risk"]["portfolio_weights"]
        .set_index("strategy")
        .loc["baseline_40_60", list(UNIVERSE)]
    )
    expected = simulate_portfolio(
        evaluation, weights, 10_000_000, 0.001, _month_ends(evaluation, "XNYS"), "baseline_40_60"
    )
    actual = evidence.tables["daily"].query(
        "period == 'evaluation' and strategy == 'baseline_40_60'"
    )
    assert actual.nav.iloc[-1] == pytest.approx(expected.daily.nav.iloc[-1])
    # A four-year validation/evaluation experiment has 2 + 0 post-funding annual changes per model.
    metrics = evidence.tables["metrics"].set_index(["period", "strategy"])
    assert metrics.loc[("validation", "annual_minimum_volatility"), "annual_target_updates"] == 2
    assert metrics.loc[("evaluation", "annual_maximum_sharpe"), "annual_target_updates"] == 0


def test_tampered_outputs_and_stale_source_are_not_displayed(experiment):
    root, path, folder, _, _ = experiment
    bundle = load_bundle(root, path)
    target_path = folder / "annual_targets.csv"
    original = target_path.read_bytes()
    target_path.write_text("changed")
    with pytest.raises(DashboardDataError, match="output changed"):
        load_adaptive(root, bundle)
    target_path.write_bytes(original)
    (root / "src/saifa/example.py").write_text("# changed source")
    with pytest.raises(DashboardDataError, match="source changed"):
        load_adaptive(root, bundle)


def test_failed_fit_marks_extension_failed_without_fallback(experiment, monkeypatch):
    root, path, folder, _, _ = experiment

    def failed(*args):
        raise RuntimeError("solver test failure")

    monkeypatch.setattr("saifa.application.adaptive_pipeline.fit_annual_targets", failed)
    with pytest.raises(RuntimeError, match="solver test failure"):
        build_adaptive(root, root / "data/snapshots/test")
    assert json.loads((folder / "manifest.json").read_text())["status"] == "failed"
    with pytest.raises(DashboardDataError, match="incomplete"):
        load_adaptive(root, load_bundle(root, path))


def test_annual_page_controls_change_period_and_objective(experiment):
    root, path, _, _, _ = experiment
    evidence = load_adaptive(root, load_bundle(root, path))

    def script(evidence):
        from saifa.dashboard.adaptive import render_annual_strategy

        render_annual_strategy(evidence)

    app = AppTest.from_function(script, args=(evidence,)).run(timeout=15)
    assert not app.exception
    explanation = app.expander[0]
    assert explanation.label == "Read explanation, methodology and limitations"
    assert not explanation.proto.expanded
    assert not explanation.selectbox
    assert explanation.info
    assert any("Annual minus frozen" in m.value for m in explanation.markdown)
    initial = app.dataframe[0].value.copy()
    assert (
        "adaptive equivalents" in app.info[0].value.lower()
        or "Adaptive equivalents" in app.info[0].value
    )
    app.selectbox(key="annual_period").set_value("validation").run()
    assert not app.exception
    assert not app.dataframe[0].value.equals(initial)
    targets = app.dataframe[1].value.copy()
    app.selectbox(key="annual_objective").set_value("maximum_sharpe").run()
    assert not app.exception
    assert not app.dataframe[1].value.equals(targets)
    assert app.dataframe[1].value.strategy.eq("annual_maximum_sharpe").all()
