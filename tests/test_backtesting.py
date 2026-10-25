"""Hand likelihoods, calendar alignment, missing evidence and past-only forecasts."""

import json
from dataclasses import replace

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from saifa.application.backtest_pipeline import build_backtest, evaluate_forecasts
from saifa.domain.config import UNIVERSE, BacktestConfig, EVTConfig, OptimisationConfig
from saifa.models.backtesting import basel_traffic_light, christoffersen_test, kupiec_test
from saifa.models.risk import empirical_tail, normal_tail
from saifa.models.walk_forward import forecast_positions, walk_forward


def panel():
    index = xcals.get_calendar("XNYS", start="2015-01-02", end="2019-02-01").sessions.tz_localize(
        None
    )
    rng = np.random.default_rng(617)
    market = rng.normal(0.0001, 0.007, (len(index), 1))
    return pd.DataFrame(
        market + rng.normal(0.0001, 0.004, (len(index), 7)), index=index, columns=UNIVERSE
    )


def portfolios():
    return {"baseline": pd.Series([0.4, 0, 0, 0.6, 0, 0, 0], index=UNIVERSE)}


def small_config(**overrides):
    return replace(
        BacktestConfig(
            start="2019-01-01",
            end_exclusive="2019-01-10",
            lookback_observations=500,
            simulations=1000,
        ),
        **overrides,
    )


def forecast(frame, config=None, **kwargs):
    return walk_forward(
        frame,
        portfolios(),
        config or small_config(),
        EVTConfig(),
        "2018-12-31",
        "2022-01-01",
        **kwargs,
    )


def test_kupiec_hand_calculation_and_boundary_likelihoods():
    hits = np.r_[np.ones(5), np.zeros(245)]
    result = kupiec_test(hits, 0.99)
    assert result.statistic == pytest.approx(1.956809788230652)
    assert result.p_value == pytest.approx(0.16185491719603548)
    assert result.exact_p_value == pytest.approx(0.10781237309637476)
    assert result.expected_exceptions == pytest.approx(2.5)
    assert result.decision == "do_not_reject"
    for hits in (np.zeros(250), np.ones(250)):
        result = kupiec_test(hits, 0.99)
        assert np.isfinite(result.statistic)
        assert result.decision == "reject"
        assert "boundary" in result.warning
    assert kupiec_test([], 0.99).decision == "unavailable"


def test_independence_hand_counts_and_likelihood():
    hits = [0, 0, 1, 0, 1, 1, 0, 0, 0, 1] * 2
    result = christoffersen_test(hits)
    assert (result.n00, result.n01, result.n10, result.n11) == (6, 6, 5, 2)
    assert result.statistic == pytest.approx(0.8526139662509244)
    assert result.p_value == pytest.approx(0.35581390967068993)
    assert result.decision == "do_not_reject"
    assert "sparse" in result.warning


def test_same_exception_rate_can_have_different_clustering():
    scattered, clustered = np.zeros(1000), np.zeros(1000)
    scattered[np.arange(10, 1000, 50)] = 1
    clustered[100:120] = 1
    assert kupiec_test(scattered, 0.98).statistic == pytest.approx(0)
    assert kupiec_test(clustered, 0.98).statistic == pytest.approx(0)
    assert christoffersen_test(scattered).decision == "do_not_reject"
    assert christoffersen_test(clustered).decision == "reject"


def test_missing_forecasts_are_not_dropped_or_joined_and_sparse_is_not_pass():
    hits = [0, 1, None, 1, 0]
    coverage = kupiec_test(hits, 0.99)
    assert coverage.missing_forecasts == 1
    assert coverage.p_value is None and coverage.decision == "unavailable"
    independence = christoffersen_test(hits)
    assert (independence.n00, independence.n01, independence.n10, independence.n11) == (0, 1, 1, 0)
    assert independence.p_value is None
    for hits in ([], [0], np.zeros(1000), np.r_[np.zeros(249), 1]):
        result = christoffersen_test(hits)
        assert result.decision == "unavailable" and result.p_value is None


@pytest.mark.parametrize(
    "count,zone",
    [(0, "green"), (4, "green"), (5, "yellow"), (9, "yellow"), (10, "red"), (250, "red")],
)
def test_basel_exact_boundaries(count, zone):
    result = basel_traffic_light(np.r_[np.ones(count), np.zeros(250 - count)], 0.99)
    assert result.zone == zone and result.exceptions == count and result.status == "ok"


def test_basel_no_silent_window_or_confidence_adaptation():
    assert basel_traffic_light(np.zeros(249), 0.99).zone is None
    assert basel_traffic_light(np.zeros(251), 0.99).zone is None
    assert basel_traffic_light(np.zeros(250), 0.95).status == "unsupported_confidence"
    assert basel_traffic_light(np.r_[np.zeros(249), np.nan], 0.99).status == "incomplete_forecasts"


@pytest.mark.parametrize("values", [[2], [np.inf], [[0, 1]], [-1]])
def test_invalid_exception_inputs(values):
    for function in (
        lambda x: kupiec_test(x, 0.99),
        christoffersen_test,
        lambda x: basel_traffic_light(x, 0.99),
    ):
        with pytest.raises(ValueError):
            function(values)


@pytest.mark.parametrize(
    "overrides",
    [
        {"start": "2027-01-01"},
        {"lookback_observations": 2},
        {"simulations": 2},
        {"confidence_levels": (99,)},
        {"confidence_levels": (0.99, 0.99)},
        {"significance": 0},
        {"minimum_previous_state": 0},
        {"seed": -1},
    ],
)
def test_bad_configuration(overrides):
    with pytest.raises(ValueError):
        BacktestConfig(**overrides)


def test_forecast_window_hand_alignment_holiday_and_moments():
    frame = panel()
    config = small_config(simulations=100000)
    result = forecast(frame, config)
    first = result.iloc[0]
    assert first.forecast_date == "2019-01-02" and first.as_of == "2018-12-31"
    position = frame.index.get_loc("2019-01-02")
    history = frame.iloc[position - 500 : position]
    assert first.window_start == str(history.index[0].date())
    expected = empirical_tail(-(history @ portfolios()["baseline"]).to_numpy(), 0.95)
    assert first.var_fraction == pytest.approx(expected.var_fraction)
    assert first.loss_fraction == pytest.approx(-frame.loc["2019-01-02"] @ portfolios()["baseline"])
    assert (pd.to_datetime(result.as_of) < pd.to_datetime(result.forecast_date)).all()
    assert np.allclose(result.var_usd, result.var_fraction * 10_000_000, equal_nan=True)
    w = portfolios()["baseline"].to_numpy()
    sigma = np.sqrt(w @ history.cov().to_numpy() @ w)
    expected = normal_tail(float(history.mean() @ w), sigma, 0.99)
    normal = result.loc[
        (result.forecast_date == "2019-01-02")
        & (result.method == "parametric_normal")
        & (result.confidence == 0.99)
    ].iloc[0]
    assert normal.var_fraction == pytest.approx(expected.var_fraction)
    assert normal.es_fraction == pytest.approx(expected.es_fraction)
    mc = result.loc[
        (result.forecast_date == "2019-01-02")
        & (result.method == "monte_carlo_normal")
        & (result.confidence == 0.99)
    ].iloc[0]
    assert abs(mc.var_fraction - normal.var_fraction) < 0.04 * sigma
    assert abs(mc.es_fraction - normal.es_fraction) < 0.05 * sigma


def test_forecast_excludes_target_return_and_future_data():
    frame = panel()
    config = small_config()
    before = forecast(frame, config)
    changed = frame.copy()
    changed.loc["2019-01-04":] = -0.8
    after = forecast(changed, config)
    earlier = before.forecast_date < "2019-01-04"
    pd.testing.assert_frame_equal(before.loc[earlier], after.loc[earlier])
    target = before.forecast_date == "2019-01-04"
    # The target-day shock alters realized losses, not the forecasts issued the previous close.
    columns = ["var_fraction", "es_fraction", "evt_threshold", "evt_shape", "evt_scale"]
    pd.testing.assert_frame_equal(before.loc[target, columns], after.loc[target, columns])
    assert not np.array_equal(
        before.loc[target, "loss_fraction"], after.loc[target, "loss_fraction"]
    )
    frame.loc["2019-01-10":] = 100
    pd.testing.assert_frame_equal(before, forecast(frame, config))


def test_date_seed_range_invariance_and_named_portfolio_order():
    frame = panel()
    config = small_config()
    first = forecast(frame, config)
    short = forecast(frame, replace(config, start="2019-01-04"))
    pd.testing.assert_frame_equal(
        first.loc[first.forecast_date >= "2019-01-04"].reset_index(drop=True), short
    )
    named = portfolios()
    named = {"copy": named["baseline"].iloc[::-1], **named}
    duplicate = walk_forward(frame, named, config, EVTConfig(), "2018-12-31", "2022-01-01")
    pd.testing.assert_frame_equal(
        first, duplicate.loc[duplicate.strategy == "baseline"].reset_index(drop=True)
    )
    other = forecast(frame, replace(config, seed=101))
    same = first.method != "monte_carlo_normal"
    pd.testing.assert_frame_equal(first.loc[same], other.loc[same])
    assert not first.loc[~same, "var_fraction"].equals(other.loc[~same, "var_fraction"])


def test_gain_sign_equality_and_unavailable_evt():
    frame = panel() * 0
    frame["SPY"] = 0.0078125  # Exactly representable binary fraction avoids rounding in tie check.
    weights = pd.Series([1, 0, 0, 0, 0, 0, 0], index=UNIVERSE)
    result = walk_forward(
        frame, {"single": weights}, small_config(), EVTConfig(), "2018-12-31", "2022-01-01"
    )
    valid = result.loc[result.method != "evt_pot_gpd"]
    assert valid.exception.eq(0).all()
    assert valid.var_fraction.eq(-0.0078125).all()
    invalid = result.loc[result.method == "evt_pot_gpd"]
    assert invalid.exception.isna().all()
    assert invalid.status.eq("insufficient_exceedances").all()


def test_calendar_gaps_short_history_and_future_weight_cutoff_rejected():
    frame = panel()
    with pytest.raises(ValueError, match="missing observed"):
        forecast(frame.drop(pd.Timestamp("2019-01-03")))
    with pytest.raises(ValueError, match="consecutive"):
        forecast(frame.drop(pd.Timestamp("2018-12-20")))
    with pytest.raises(ValueError, match="Insufficient"):
        forecast(frame.tail(100))
    with pytest.raises(ValueError, match="after the first"):
        walk_forward(frame, portfolios(), small_config(), EVTConfig(), "2019-01-02", "2022-01-01")
    with pytest.raises(ValueError, match="unique ordered"):
        forecast_positions(frame.iloc[::-1], small_config())


def test_rolling_basel_resets_period_and_does_not_skip_missing_forecasts():
    dates = (
        xcals.get_calendar("XNYS", start="2020-01-01", end="2022-01-01")
        .sessions[:500]
        .strftime("%Y-%m-%d")
    )
    rows = pd.DataFrame(
        {
            "period": ["validation"] * 250 + ["evaluation"] * 250,
            "strategy": "baseline",
            "method": "evt",
            "confidence": 0.99,
            "forecast_date": dates,
            "exception": 0.0,
        }
    )
    rows.loc[255, "exception"] = np.nan
    summary, lights = evaluate_forecasts(rows, small_config())
    assert lights.loc[249, "zone"] == "green"
    assert lights.loc[250, "observations"] == 1
    assert lights.loc[499, "status"] == "incomplete_forecasts"
    assert summary.iloc[-1].coverage_decision == "unavailable"
    assert summary.iloc[-1].independence_decision == "unavailable"
    with pytest.raises(ValueError, match="consecutive exchange"):
        evaluate_forecasts(rows.drop(index=255), small_config())


def test_pipeline_frozen_weights_provenance_failed_status_and_repeatability(tmp_path):
    snapshot = tmp_path / "data/snapshots/test"
    snapshot.mkdir(parents=True)
    (snapshot / "manifest.json").write_text("{}")
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    frame = panel()
    frame.to_csv(inputs / "simple_returns.csv", index_label="Date")
    rates = pd.DataFrame({"simple_return": 0.00001}, index=frame.index)
    rates.to_csv(inputs / "risk_free_returns.csv", index_label="Date")

    def builder(root, path):
        return inputs

    config = small_config(lookback_observations=250)
    policy = OptimisationConfig(
        validation_end_exclusive="2019-01-07", evaluation_end_exclusive="2020-01-01"
    )
    output = build_backtest(tmp_path, snapshot, config, policy=policy, data_builder=builder)
    forecasts = pd.read_csv(output / "forecasts.csv")
    assert len(forecasts) == 6 * 3 * 4 * 2
    assert forecasts.weights_as_of.eq("2018-12-31").all()
    assert set(forecasts.period) == {"validation", "evaluation"}
    assert forecasts.loc[forecasts.method.eq("evt_pot_gpd"), "exception"].isna().all()
    meta = json.loads((output / "summary.json").read_text())
    assert meta["model_selection"].startswith("none")
    assert meta["review_record"] == "docs/final/07-backtesting/03-manual-backtest-check.md"
    assert json.loads((output / "status.json").read_text())["status"] == "complete"
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    # Future risk-free and asset returns cannot affect frozen weights or forecasts.
    frame.loc["2019-01-10":] = 100
    rates.loc["2019-01-01":] = 100
    frame.to_csv(inputs / "simple_returns.csv", index_label="Date")
    rates.to_csv(inputs / "risk_free_returns.csv", index_label="Date")
    assert build_backtest(tmp_path, snapshot, config, policy=policy, data_builder=builder) == output
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    with pytest.raises(ValueError, match="after development"):
        build_backtest(
            tmp_path, snapshot, replace(config, start="2018-12-20"), data_builder=builder
        )
    with pytest.raises(ValueError, match="missing observed"):
        build_backtest(
            tmp_path, snapshot, replace(config, end_exclusive="2019-03-01"), data_builder=builder
        )
    statuses = [
        json.loads(p.read_text())["status"]
        for p in (tmp_path / "output/backtest").rglob("status.json")
    ]
    assert set(statuses) == {"complete", "failed"}
