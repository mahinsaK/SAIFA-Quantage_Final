"""Independent derivative, additivity, tie, calendar and wealth-path checks."""

import json
from dataclasses import replace

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from src.application.stress_pipeline import build_stress
from src.domain.config import (
    UNIVERSE,
    HistoricalStressPeriod,
    OptimisationConfig,
    RiskConfig,
    StressConfig,
)
from src.models.contributions import (
    funded_transfer_checks,
    historical_es_contributions,
    normal_contributions,
)
from src.models.risk import empirical_tail, normal_tail
from src.models.stress import historical_replay, joint_shock


def diagonal_panel():
    a, b = np.sqrt(1.5) * 0.02, np.sqrt(1.5) * 0.01
    return pd.DataFrame(
        {"A": np.array([-a, a, 0, 0]) + 0.001, "B": np.array([0, 0, -b, b]) + 0.0002}
    )


def test_normal_hand_example_mean_term_and_additivity():
    weights = pd.Series({"A": 0.4, "B": 0.6})
    var, es = normal_contributions(diagonal_panel(), weights, 0.95)
    assert var.total_fraction == pytest.approx(0.0159285362695147)
    assert es.total_fraction == pytest.approx(0.0201071280750743)
    assert [a.component_fraction for a in var.assets] == pytest.approx(
        [0.0101270632124894, 0.0058014730570253]
    )
    for result in (var, es):
        assert sum(a.component_fraction for a in result.assets) == pytest.approx(
            result.total_fraction
        )
        assert sum(a.share_percent for a in result.assets) == pytest.approx(100)


def test_normal_marginals_match_independent_central_differences():
    returns = diagonal_panel()
    w = pd.Series({"A": 0.4, "B": 0.6})
    mean, covariance = returns.mean().to_numpy(), returns.cov().to_numpy()

    def total(values, measure):
        sigma = np.sqrt(values @ covariance @ values)
        return getattr(normal_tail(values @ mean, sigma, 0.99), f"{measure}_fraction")

    for result in normal_contributions(returns, w, 0.99):
        for i, asset in enumerate(result.assets):
            delta = np.zeros(2)
            delta[i] = 1e-6
            derivative = (
                total(w.to_numpy() + delta, result.measure)
                - total(w.to_numpy() - delta, result.measure)
            ) / (2e-6)
            assert asset.marginal_fraction == pytest.approx(derivative, abs=1e-10)


def test_hedge_negative_components_zero_holdings_and_label_order():
    x = np.linspace(-0.03, 0.03, 101)
    returns = pd.DataFrame({"A": x, "B": -0.5 * x, "C": 0.0})
    w = pd.Series({"A": 0.8, "B": 0.2, "C": 0.0})
    for result in (
        *normal_contributions(returns, w, 0.95),
        historical_es_contributions(returns, w, 0.95),
    ):
        assert result.assets[1].component_fraction < 0
        assert result.assets[0].share_percent > 100
        assert result.assets[2].component_fraction == 0
        assert sum(a.component_fraction for a in result.assets) == pytest.approx(
            result.total_fraction
        )
    assert normal_contributions(returns, w, 0.95) == normal_contributions(
        returns, w.iloc[::-1], 0.95
    )


def test_zero_assets_and_zero_volatility_hedge_have_distinct_gradients():
    weights = pd.Series({"A": 0.5, "B": 0.5})
    constant = pd.DataFrame({"A": [0.01] * 10, "B": [0.01] * 10})
    for result in normal_contributions(constant, weights, 0.99):
        assert result.total_fraction == pytest.approx(-0.01)
        assert sum(a.component_fraction for a in result.assets) == pytest.approx(-0.01)
    for result in normal_contributions(constant * 0, weights, 0.99):
        assert result.total_fraction == 0 and result.assets[0].share_percent is None
    x = np.linspace(-0.02, 0.02, 100)
    for result in normal_contributions(pd.DataFrame({"A": x, "B": -x}), weights, 0.99):
        assert result.status == "undefined_gradient"
        assert all(a.component_fraction is None for a in result.assets)


def test_empirical_es_ties_share_probability_mass_and_ignore_row_order():
    losses = pd.DataFrame({"A": [0.04, 0.02, 0.03, 0], "B": [0, 0.02, 0.01, 0]})
    weights = pd.Series({"A": 0.5, "B": 0.5})
    result = historical_es_contributions(-losses, weights, 0.5)
    assert result.status == "tie_subgradient"
    assert result.total_fraction == pytest.approx(0.02)
    assert [a.component_fraction for a in result.assets] == pytest.approx([0.015, 0.005])
    assert result == historical_es_contributions(-losses.iloc[::-1], weights, 0.5)


def test_empirical_fractional_mass_and_local_funded_derivative():
    losses = pd.DataFrame({"A": np.arange(6) / 100, "B": np.arange(6) / 200})
    w = pd.Series({"A": 0.4, "B": 0.6})
    result = historical_es_contributions(-losses, w, 0.75)
    assert result.total_fraction == pytest.approx((0.5 * 0.028 + 0.035) / 1.5)
    assert sum(a.component_fraction for a in result.assets) == pytest.approx(result.total_fraction)
    step = 1e-5
    changed = w + pd.Series({"A": step, "B": -step})
    recalculated = empirical_tail((losses @ changed).to_numpy(), 0.75).es_fraction
    linear = step * (result.assets[0].marginal_fraction - result.assets[1].marginal_fraction)
    assert recalculated - result.total_fraction == pytest.approx(linear, abs=1e-12)
    larger = historical_es_contributions(-losses * 2, w, 0.75)
    assert larger.total_fraction == pytest.approx(2 * result.total_fraction)


@pytest.mark.parametrize("bad", [0, 1, 99, np.nan])
def test_invalid_confidence_rejected(bad):
    for function in (normal_contributions, historical_es_contributions):
        with pytest.raises(ValueError):
            function(diagonal_panel(), pd.Series({"A": 0.4, "B": 0.6}), bad)


def tiny_replay(values, level=0.15):
    frame = pd.DataFrame(
        values, index=pd.to_datetime(["2020-01-02", "2020-01-03"]), columns=["A", "B"]
    )
    return historical_replay(
        frame,
        pd.Series({"A": 0.5, "B": 0.5}),
        HistoricalStressPeriod("example", "2020-01-01", "2020-01-04"),
        1000,
        "equal",
        "2018-12-31",
        level,
    )


def test_buy_and_hold_hand_path_includes_initial_close_and_drifting_weights():
    run = tiny_replay([[-0.2, 0], [0.25, 0]])
    assert run.summary.base_date == "2019-12-31"
    assert run.path.nav.tolist() == pytest.approx([1000, 900, 1000])
    assert run.path.A_weight.iloc[1] == pytest.approx(400 / 900)
    assert run.summary.maximum_drawdown_fraction == pytest.approx(0.1)
    assert run.summary.terminal_loss_usd == pytest.approx(0)
    assert run.summary.worst_loss_from_initial_usd == pytest.approx(100)
    assert run.components.terminal_loss_usd.sum() == pytest.approx(0)


def test_drawdown_dollar_uses_actual_peak_not_initial_nav():
    run = tiny_replay([[0.1, 0.1], [-0.2, -0.2]])
    assert run.path.nav.tolist() == pytest.approx([1000, 1100, 880])
    assert run.summary.terminal_loss_usd == pytest.approx(120)
    assert run.summary.maximum_drawdown_fraction == pytest.approx(0.2)
    assert run.summary.drawdown_usd_at_max_fraction == pytest.approx(220)
    assert run.summary.peak_date == "2020-01-02"
    assert run.summary.trough_date == "2020-01-03"
    assert run.summary.review_trigger_breached


def test_replay_flags_allocations_fitted_after_crisis():
    frame = pd.DataFrame(
        {"A": [-0.1, 0.1], "B": [0, 0]},
        index=pd.to_datetime(["2020-01-02", "2020-01-03"]),
    )
    run = historical_replay(
        frame,
        pd.Series({"A": 0.5, "B": 0.5}),
        HistoricalStressPeriod("example", "2020-01-01", "2020-01-04"),
        1000,
        "test",
        "2021-12-31",
        0.15,
    )
    assert run.summary.status == "ok"
    assert not run.summary.weights_available_at_start
    assert "Not a historical investment track record" in run.summary.warning


def test_total_loss_remains_zero_without_division_by_zero():
    run = tiny_replay([[-1, -1], [0.2, 0.1]])
    assert run.path.nav.tolist() == [1000, 0, 0]
    assert np.isnan(run.path.daily_return.iloc[-1])
    assert run.summary.maximum_drawdown_fraction == 1
    assert run.summary.terminal_loss_usd == 1000


def test_missing_or_invalid_crisis_input_is_unavailable_not_truncated():
    period = HistoricalStressPeriod("test", "2020-01-01", "2020-01-04")
    frame = pd.DataFrame({"A": [0.1], "B": [0]}, index=pd.to_datetime(["2020-01-03"]))
    w = pd.Series({"A": 0.5, "B": 0.5})
    run = historical_replay(frame, w, period, 1000, "test", "2021-01-01", 0.15)
    assert run.summary.status == "unavailable" and run.path.empty
    assert run.summary.expected_sessions == 2 and run.summary.observed_sessions == 1
    invalid = tiny_replay([[np.nan, 0], [0, 0]])
    assert invalid.summary.status == "unavailable"
    invalid = tiny_replay([[-1.1, 0], [0, 0]])
    assert invalid.summary.status == "unavailable"


def test_joint_shock_hand_values_negative_offset_and_severity():
    w = pd.Series({"A": 0.4, "B": 0.6})
    run = joint_shock(w, pd.Series({"B": 0.05, "A": -0.20}), 10_000_000, "test", "shock", 1, 0.1)
    assert run.summary.loss_fraction == pytest.approx(0.05)
    assert run.summary.loss_usd == pytest.approx(500_000)
    assert run.components.loss_usd.sum() == pytest.approx(500_000)
    assert run.components.loc[run.components.ticker == "B", "loss_usd"].iloc[0] == pytest.approx(
        -300_000
    )
    larger = joint_shock(
        w, pd.Series({"A": -0.20, "B": 0.05}), 20_000_000, "test", "shock", 1.5, 0.1
    )
    assert larger.summary.loss_usd == pytest.approx(1_500_000)


@pytest.mark.parametrize(
    "shocks",
    [
        pd.Series({"A": -0.2}),
        pd.Series({"A": np.nan, "B": 0}),
        pd.Series({"A": -1.1, "B": 0}),
        pd.Series([0, 0], index=["A", "A"]),
    ],
)
def test_invalid_shock_vectors_rejected(shocks):
    with pytest.raises(ValueError):
        joint_shock(pd.Series({"A": 0.4, "B": 0.6}), shocks, 1000, "test", "shock", 1, 0.1)


@pytest.mark.parametrize(
    "changes",
    [
        {"shock_multipliers": (0, 1)},
        {"shock_multipliers": (0.5,)},
        {"shocks": (("SPY", -0.2),)},
        {"transfer_weight": 0},
        {"drawdown_review_level": np.nan},
        {"historical_periods": ()},
    ],
)
def test_bad_stress_config(changes):
    with pytest.raises(ValueError):
        replace(StressConfig(), **changes)


def test_funded_transfers_check_policy_and_reprice_risk():
    rng = np.random.default_rng(2026)
    frame = pd.DataFrame(rng.normal(0.0001, 0.01, (500, 7)), columns=UNIVERSE)
    w = pd.Series([0.4, 0, 0, 0.6, 0, 0, 0], index=UNIVERSE)
    results = funded_transfer_checks(frame, w, 0.99, 0.01, OptimisationConfig())
    assert len(results) == 42 * 3
    assert not results.loc[results.donor == "EFA", "feasible"].any()
    assert not results.loc[(results.donor == "SPY") & (results.receiver == "AGG"), "feasible"].any()
    selected = results.loc[(results.donor == "AGG") & (results.receiver == "SPY")]
    assert selected.feasible.all()
    changed = w.copy()
    changed["AGG"] -= 0.01
    changed["SPY"] += 0.01
    expected = historical_es_contributions(frame, changed, 0.99).total_fraction
    assert selected.loc[selected.method == "historical", "after_fraction"].iloc[0] == pytest.approx(
        expected
    )


def test_pipeline_future_isolation_unavailable_periods_provenance_and_repeatability(tmp_path):
    dates = xcals.get_calendar("XNYS", start="2015-01-02", end="2020-04-30").sessions.tz_localize(
        None
    )
    rng = np.random.default_rng(117)
    frame = pd.DataFrame(rng.normal(0.0001, 0.007, (len(dates), 7)), index=dates, columns=UNIVERSE)
    rates = pd.DataFrame({"simple_return": 0.00001}, index=dates)
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    snapshot = tmp_path / "data/snapshots/test"
    snapshot.mkdir(parents=True)
    (snapshot / "manifest.json").write_text("{}")

    def save():
        frame.to_csv(inputs / "simple_returns.csv", index_label="Date")
        rates.to_csv(inputs / "risk_free_returns.csv", index_label="Date")

    def builder(root, path):
        return inputs

    save()
    config = RiskConfig(as_of="2020-03-31", lookback_observations=250)
    output = build_stress(tmp_path, snapshot, config, data_builder=builder)
    summary = pd.read_csv(output / "contribution_summary.csv")
    assert len(summary) == 18
    assert summary.reconciliation_error_fraction.abs().max() < 1e-12
    assert len(pd.read_csv(output / "asset_contributions.csv")) == 126
    history = pd.read_csv(output / "historical_summary.csv")
    assert history.status.value_counts().to_dict() == {"unavailable": 6, "ok": 3}
    assert len(pd.read_csv(output / "hypothetical_summary.csv")) == 9
    assert json.loads((output / "status.json").read_text())["status"] == "complete"
    meta = json.loads((output / "summary.json").read_text())
    assert meta["human_validation"] == "pending"
    assert meta["weights_as_of"] == "2018-12-31"
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    frame.loc["2020-04-01":] = -0.95
    rates.loc["2019-01-01":] = 100
    save()
    build_stress(tmp_path, snapshot, config, data_builder=builder)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError, match="precedes"):
        build_stress(tmp_path, snapshot, replace(config, as_of="2018-12-31"), data_builder=builder)
    statuses = [
        json.loads(p.read_text())["status"]
        for p in (tmp_path / "output/stress").rglob("status.json")
    ]
    assert set(statuses) == {"complete", "failed"}
