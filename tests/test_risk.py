"""Hand examples, analytic identities, simulation error and date-isolation checks."""

import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from saifa.application.risk_pipeline import build_risk
from saifa.domain.config import UNIVERSE, OptimisationConfig, RiskConfig
from saifa.models.optimisation import fit_target_allocations
from saifa.models.risk import (
    compare_risk,
    empirical_tail,
    fit_gaussian,
    gaussian_scenarios,
    normal_tail,
    select_risk_window,
)


def returns_panel():
    rng = np.random.default_rng(314)
    market = rng.normal(0.0002, 0.008, (1_000, 1))
    values = market + rng.normal(0, 0.004, (1_000, 7))
    return pd.DataFrame(values, columns=UNIVERSE, index=pd.bdate_range("2019-01-02", periods=1_000))


def baseline_weights():
    return pd.Series([0.4, 0, 0, 0.6, 0, 0, 0], index=UNIVERSE)


def test_hand_holdings_loss_is_not_a_weighted_average_of_asset_var():
    # Same paired asset move on every observation gives a deterministic portfolio loss.
    panel = pd.DataFrame(0.0, index=range(1_000), columns=UNIVERSE)
    panel["SPY"] = -0.02
    panel["AGG"] = 0.005
    results = compare_risk(panel, {"baseline": baseline_weights()}, RiskConfig(simulations=1_000))
    for result in results:
        assert result.var_fraction == pytest.approx(0.005)
        assert result.es_usd == pytest.approx(50_000)


def test_zero_risk_and_90_percent_interface_confidence():
    panel = pd.DataFrame(0.0, index=range(1_000), columns=UNIVERSE)
    config = RiskConfig(confidence_levels=(0.90,), simulations=1_000)
    estimates = compare_risk(panel, {"baseline": baseline_weights()}, config)
    assert len(estimates) == 3
    assert all(r.var_usd == 0 and r.es_usd == 0 for r in estimates)
    assert "Fewer than 100" not in estimates[-1].warning


def test_parametric_moments_match_direct_daily_portfolio_statistics():
    panel = returns_panel()
    series = panel @ baseline_weights()
    expected = normal_tail(series.mean(), series.std(ddof=1), 0.99)
    estimates = compare_risk(panel, {"baseline": baseline_weights()}, RiskConfig(simulations=1_000))
    actual = next(r for r in estimates if r.method == "parametric_normal" and r.confidence == 0.99)
    assert actual.var_fraction == pytest.approx(expected.var_fraction)
    assert actual.es_fraction == pytest.approx(expected.es_fraction)


def test_empirical_hand_example_and_fractional_tail_mass():
    # 100 equiprobable losses 0.0%, 0.1%, ..., 9.9%.
    losses = np.arange(100) / 1_000
    at95 = empirical_tail(losses, 0.95)
    at99 = empirical_tail(losses, 0.99)
    assert at95.var_fraction == pytest.approx(0.094)
    assert at95.es_fraction == pytest.approx(0.097)
    assert at99.var_fraction == pytest.approx(0.098)
    assert at99.es_fraction == pytest.approx(0.099)
    fractional = empirical_tail(losses, 0.955)
    assert fractional.var_fraction == pytest.approx(0.095)
    assert fractional.es_fraction == pytest.approx(
        (0.096 + 0.097 + 0.098 + 0.099 + 0.5 * 0.095) / 4.5
    )


def test_empirical_ties_do_not_average_all_observations_at_var_boundary():
    losses = np.array([0.01] * 9 + [0.10])
    result = empirical_tail(losses, 0.8)
    assert result.var_fraction == pytest.approx(0.01)
    assert result.es_fraction == pytest.approx(0.055)


def test_gaussian_hand_example_and_degenerate_distribution():
    result = normal_tail(0.001, 0.02, 0.95)
    assert result.var_fraction == pytest.approx(0.03189707254)
    assert result.es_fraction == pytest.approx(0.04025425615)
    assert normal_tail(0.01, 0, 0.99).var_fraction == pytest.approx(-0.01)
    assert normal_tail(0.01, 0, 0.99).es_fraction == pytest.approx(-0.01)


def test_signed_gain_threshold_and_positive_homogeneity():
    losses = -np.arange(1, 101) / 1_000
    tail = empirical_tail(losses, 0.95)
    scaled = empirical_tail(3 * losses, 0.95)
    assert tail.var_fraction < 0 and tail.es_fraction < 0
    assert scaled.var_fraction == pytest.approx(3 * tail.var_fraction)
    assert scaled.es_fraction == pytest.approx(3 * tail.es_fraction)


@pytest.mark.parametrize(
    "losses, confidence", [([], 0.95), ([np.nan], 0.95), ([[1]], 0.95), ([1], 1), ([1], 95)]
)
def test_bad_tail_inputs_rejected(losses, confidence):
    with pytest.raises(ValueError):
        empirical_tail(np.array(losses), confidence)


def test_simulation_preserves_dependence_and_handles_singular_covariance():
    values = np.linspace(-0.03, 0.03, 1_000)
    panel = pd.DataFrame({"A": values, "B": -values})
    scenarios = gaussian_scenarios(fit_gaussian(panel), 20_000, 7)
    # Perfect offsets cancel risk; independently simulating each column would fail this.
    assert np.max(np.abs(scenarios @ np.array([0.5, 0.5]))) < 1e-10
    assert scenarios[:, 0].std(ddof=1) == pytest.approx(values.std(ddof=1), rel=0.03)


def test_all_models_currency_scaling_monotonicity_es_order_and_seed():
    panel = returns_panel()
    config = RiskConfig(simulations=50_000)
    portfolios = {"baseline": baseline_weights()}
    first = compare_risk(panel, portfolios, config)
    assert first == compare_risk(panel, portfolios, config)
    scaled = compare_risk(panel, portfolios, replace(config, reference_nav=20_000_000))
    for original, larger in zip(first, scaled):
        assert original.es_fraction >= original.var_fraction
        assert original.var_usd == pytest.approx(original.var_fraction * 10_000_000)
        assert original.es_usd == pytest.approx(original.es_fraction * 10_000_000)
        assert larger.var_usd == pytest.approx(2 * original.var_usd)
        assert larger.es_fraction == original.es_fraction
        assert original.var_percent == pytest.approx(100 * original.var_fraction)
    for method in {r.method for r in first}:
        lower, higher = [r for r in first if r.method == method]
        assert higher.var_fraction >= lower.var_fraction
        assert higher.es_fraction >= lower.es_fraction
    different_seed = compare_risk(panel, portfolios, replace(config, seed=43))
    assert first[0] == different_seed[0]  # Historical result never uses randomness.
    assert first[1] == different_seed[1]
    assert first[2].var_fraction != different_seed[2].var_fraction
    assert "Fewer than 20" in first[3].warning


def test_monte_carlo_converges_to_analytic_normal_with_reported_simulation_error():
    results = compare_risk(returns_panel(), {"baseline": baseline_weights()}, RiskConfig())
    for confidence in (0.95, 0.99):
        normal = next(
            r for r in results if r.confidence == confidence and r.method == "parametric_normal"
        )
        mc = next(
            r for r in results if r.confidence == confidence and r.method == "monte_carlo_normal"
        )
        assert abs(mc.var_fraction - normal.var_fraction) < 5 * mc.mc_var_standard_error
        assert abs(mc.es_fraction - normal.es_fraction) < 5 * mc.mc_es_standard_error


def test_column_order_and_portfolio_order_do_not_change_named_results():
    panel = returns_panel()
    weights = baseline_weights()
    a = compare_risk(panel, {"baseline": weights}, RiskConfig(simulations=1_000))
    b = compare_risk(panel, {"baseline": weights.iloc[::-1]}, RiskConfig(simulations=1_000))
    assert a == b  # Weight labels, not Series order, determine portfolio exposures.
    c = compare_risk(panel, {"copy": weights, "baseline": weights}, RiskConfig(simulations=1_000))
    assert a == tuple(r for r in c if r.strategy == "baseline")


def test_future_returns_never_enter_selected_window_or_change_estimates():
    panel = returns_panel()
    config = RiskConfig(
        as_of=str(panel.index[700].date()), lookback_observations=500, simulations=1_000
    )
    window = select_risk_window(panel, config)
    changed = panel.copy()
    changed.iloc[701:] = 100  # Deliberately impossible future returns must not enter today's fit.
    pd.testing.assert_frame_equal(window, select_risk_window(changed, config))
    assert window.index[-1] == panel.index[700]
    assert window.index[0] == panel.index[201]
    assert compare_risk(window, {"baseline": baseline_weights()}, config) == compare_risk(
        select_risk_window(changed, config), {"baseline": baseline_weights()}, config
    )


def test_missing_dates_short_history_and_invalid_inputs_fail_explicitly():
    panel = returns_panel()
    with pytest.raises(ValueError, match="observed trading"):
        select_risk_window(panel, RiskConfig(as_of="2019-01-05"))
    with pytest.raises(ValueError, match="Insufficient"):
        select_risk_window(panel.iloc[:100], RiskConfig())
    with pytest.raises(ValueError, match="unique ordered"):
        select_risk_window(panel.iloc[::-1], RiskConfig())
    panel.iloc[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        compare_risk(panel, {"baseline": baseline_weights()}, RiskConfig(simulations=1_000))
    with pytest.raises(ValueError, match="match each asset"):
        compare_risk(
            returns_panel(), {"bad": pd.Series({"SPY": 1.0})}, RiskConfig(simulations=1_000)
        )


@pytest.mark.parametrize(
    "overrides",
    [
        {"horizon_sessions": 10},
        {"reference_nav": float("nan")},
        {"reference_nav": 0},
        {"seed": -1},
        {"simulations": 1_000.5},
        {"confidence_levels": (95, 99)},
        {"confidence_levels": (0.95, 0.95)},
        {"lookback_observations": 100},
    ],
)
def test_invalid_configuration(overrides):
    with pytest.raises(ValueError):
        RiskConfig(**overrides)


def fake_inputs(tmp_path):
    snapshot = tmp_path / "data" / "snapshots" / "test-snapshot"
    snapshot.mkdir(parents=True)
    (snapshot / "manifest.json").write_text("{}")
    data_output = tmp_path / "output/data" / snapshot.name
    data_output.mkdir(parents=True)
    panel = returns_panel()
    # Include pre-development observations for pipeline provenance.
    panel.index = pd.bdate_range("2016-01-04", periods=len(panel))
    panel.to_csv(data_output / "simple_returns.csv", index_label="Date")

    pd.DataFrame({"simple_return": 0.00001}, index=panel.index).to_csv(
        data_output / "risk_free_returns.csv", index_label="Date"
    )

    def builder(root, snapshot_path):
        return data_output

    return snapshot, builder


def test_pipeline_artifacts_reproducibility_and_settings_isolation(tmp_path):
    snapshot, builder = fake_inputs(tmp_path)
    config = RiskConfig(lookback_observations=250, simulations=1_000)
    output = build_risk(tmp_path, snapshot, config, data_builder=builder)
    results = pd.read_csv(output / "risk_estimates.csv")
    assert len(results) == 18
    assert results.groupby("strategy").size().eq(6).all()
    assert (pd.to_datetime(results.forecast_session) > pd.to_datetime(results.as_of)).all()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["human_validation"] == "pending"
    assert summary["observations"] == 250
    assert summary["weight_basis"] == "frozen_target_allocations"
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert build_risk(tmp_path, snapshot, config, data_builder=builder) == output
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    alternative = build_risk(tmp_path, snapshot, replace(config, seed=100), data_builder=builder)
    assert alternative != output
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


def test_failed_pipeline_status_and_portfolio_future_leakage_guard(tmp_path):
    snapshot, builder = fake_inputs(tmp_path)
    config = RiskConfig(as_of="2018-12-31", lookback_observations=250, simulations=1_000)
    with pytest.raises(ValueError, match="estimation cutoff"):
        build_risk(tmp_path, snapshot, config, data_builder=builder)
    statuses = list((tmp_path / "output/risk").rglob("status.json"))
    assert len(statuses) == 1
    assert json.loads(statuses[0].read_text())["status"] == "failed"
    assert not (statuses[0].parent / "summary.json").exists()


def test_early_snapshot_needs_no_evaluation_history_and_confidence_is_not_rounded(tmp_path):
    snapshot, builder = fake_inputs(tmp_path)
    config = RiskConfig(
        as_of="2019-01-02", lookback_observations=250, simulations=1_000, confidence_levels=(0.955,)
    )
    folder = builder(tmp_path, snapshot)
    for name in ("simple_returns.csv", "risk_free_returns.csv"):
        frame = pd.read_csv(folder / name, index_col="Date", parse_dates=True)
        frame.loc[: config.as_of].to_csv(folder / name, index_label="Date")
    output = build_risk(tmp_path, snapshot, config, data_builder=builder)
    report = (output / "risk_report.md").read_text()
    assert "| 95.5% |" in report
    assert "| 96% |" not in report
    assert not (tmp_path / "output/optimisation").exists()
    assert len(pd.read_csv(output / "risk_estimates.csv")) == 9


def test_real_candidate_fit_ignores_future_returns_and_rates_and_uses_configured_units():
    panel = returns_panel()
    panel.index = pd.bdate_range("2016-01-04", periods=len(panel))
    rates = pd.Series(0.00001, index=panel.index)
    config = OptimisationConfig(annual_trading_days=250)
    original = fit_target_allocations(panel, rates, config)
    future = panel.index >= config.development_end_exclusive
    panel.loc[future] = 100
    rates.loc[future] = 100
    changed = fit_target_allocations(panel, rates, config)
    assert original.annual_risk_free == pytest.approx(0.0025)
    for before, after in zip(original.candidates, changed.candidates):
        pd.testing.assert_series_equal(before.weights, after.weights)
    with pytest.raises(ValueError, match="all development dates"):
        fit_target_allocations(panel, rates.iloc[1:], config)
