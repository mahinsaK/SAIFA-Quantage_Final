"""Analytic POT checks, explicit unavailable results, resampling and leakage regressions."""

import json
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
from scipy.stats import genpareto

from saifa.application.evt_pipeline import build_evt
from saifa.domain.config import UNIVERSE, EVTConfig, RiskConfig
from saifa.domain.evt import POTFit
from saifa.models.evt import (
    bootstrap_intervals,
    bootstrap_tail,
    circular_block_sample,
    fit_pot,
    pot_tail,
    qq_diagnostics,
    threshold_diagnostics,
)


def known_fit(shape=0.2):
    return POTFit(0.9, 0.02, 1000, 100, 0.0125, shape, 0.01, 0.01 - shape * 0.02, "ok", "")


def test_hand_formula_and_exponential_limit():
    tail = pot_tail(known_fit(), 0.99)
    assert tail.var_fraction == pytest.approx(0.049244659623)
    assert tail.es_fraction == pytest.approx(0.069055824529)
    # xi=0 gives exponential excesses; near-zero shape is continuous.
    for xi in (0, 1e-10, -1e-10):
        tail = pot_tail(known_fit(xi), 0.99)
        assert tail.var_fraction == pytest.approx(0.043025850930)
        assert tail.es_fraction == pytest.approx(0.053025850930)


@pytest.mark.parametrize("shape", [-0.2, 0, 0.2, 0.7])
def test_tail_agrees_with_independent_scipy_distribution_and_conditional_mean(shape):
    fit = known_fit(shape)
    tail = pot_tail(fit, 0.99)
    excess_var = genpareto.isf(0.01 / 0.1, shape, scale=0.01)
    assert tail.var_fraction == pytest.approx(0.02 + excess_var)
    # Threshold stability: beyond this excess, beta becomes beta + xi*y.
    assert tail.es_fraction == pytest.approx(
        tail.var_fraction + genpareto.mean(shape, scale=0.01 + shape * excess_var)
    )
    assert tail.es_fraction >= tail.var_fraction
    assert pot_tail(fit, 0.95).var_fraction < tail.var_fraction
    if shape < 0:
        assert tail.es_fraction < 0.02 - 0.01 / shape


@pytest.mark.parametrize("shape", [-0.2, 0, 0.2, 0.7, 1, 1.2])
def test_threshold_boundary_is_empirical_var_and_gpd_tail_mean(shape):
    fit = known_fit(shape)
    tail = pot_tail(fit, 0.9)
    assert tail.var_fraction == fit.threshold
    assert "Threshold-boundary" in tail.warning
    if shape < 1:
        assert tail.status == "ok"
        assert tail.es_fraction == pytest.approx(
            fit.threshold + genpareto.mean(shape, scale=fit.scale)
        )
        assert pot_tail(fit, 0.9 + 1e-8).var_fraction == pytest.approx(tail.var_fraction)
    else:
        assert tail.status == "infinite_mean"
        assert tail.es_fraction is None


def test_unsupported_confidence_infinite_es_and_unbounded_losses_are_not_fabricated():
    for confidence in (0.8, 0.9 - 1e-8):
        result = pot_tail(known_fit(), confidence)
        assert result.status == "below_tail_domain"
        assert result.var_fraction is None and result.es_fraction is None
    for xi in (1, 1.2):
        tail = pot_tail(known_fit(xi), 0.99)
        assert tail.var_fraction is not None
        assert tail.es_fraction is None
        assert tail.status == "infinite_mean"
    tail = pot_tail(known_fit(0.8), 0.9999)
    assert tail.es_fraction > 1 and "above 100%" in tail.warning
    for confidence in (float("nan"), 0, 1, 99):
        with pytest.raises(ValueError):
            pot_tail(known_fit(), confidence)


def test_known_gpd_recovery_units_translation_and_qq():
    # Deterministic probability grid avoids a flaky finite random-sample assertion.
    sample = genpareto.ppf((np.arange(10000) + 0.5) / 10000, 0.2, scale=0.01)
    fitted = fit_pot(sample, 0.9)
    assert fitted.status == "ok"
    assert fitted.shape == pytest.approx(0.2, abs=0.03)
    tail = pot_tail(fitted, 0.99)
    assert tail.var_fraction == pytest.approx(genpareto.ppf(0.99, 0.2, scale=0.01), rel=0.01)
    scaled = fit_pot(3 * sample + 0.05, 0.9)
    assert scaled.shape == pytest.approx(fitted.shape, abs=1e-5)
    assert scaled.scale == pytest.approx(3 * fitted.scale, rel=1e-5)
    assert pot_tail(scaled, 0.99).es_fraction == pytest.approx(
        3 * tail.es_fraction + 0.05, rel=1e-5
    )
    qq = qq_diagnostics(sample, fitted)
    assert len(qq) == fitted.exceedances
    assert np.isfinite(qq.to_numpy()).all()


def test_actual_strict_exceedance_count_handles_ties_and_missing_tail():
    losses = np.r_[np.zeros(950), np.linspace(0.001, 0.05, 50)]
    fit = fit_pot(losses, 0.9, 50)
    assert fit.exceedances == 50 and fit.threshold == 0
    # Requested 90% quantile is actually at empirical CDF 95% due to ties.
    assert pot_tail(replace(fit, status="ok"), 0.90).status == "below_tail_domain"
    assert pot_tail(replace(fit, status="ok"), 0.95).var_fraction == fit.threshold
    assert fit_pot(losses, 0.99).status == "insufficient_exceedances"
    constant = fit_pot(np.zeros(1000), 0.9)
    assert constant.status == "insufficient_exceedances"
    assert qq_diagnostics(np.zeros(1000), constant).empty
    assert fit_pot(np.r_[np.zeros(900), np.ones(100)], 0.9).status == "degenerate_tail"
    nonregular = fit_pot(np.linspace(0, 0.1, 1000), 0.9)
    assert nonregular.status == "nonregular_fit"
    assert pot_tail(nonregular, 0.99).var_fraction is None


def test_optimizer_failure_is_explicit(monkeypatch):
    def fail(*args, **kwargs):
        raise ValueError("synthetic convergence failure")

    monkeypatch.setattr("saifa.models.evt.genpareto.fit", fail)
    fit = fit_pot(np.linspace(0, 1, 1000), 0.9)
    assert fit.status == "fit_failed"
    assert "convergence" in fit.warning


@pytest.mark.parametrize(
    "losses,q",
    [([], 0.9), ([1, np.nan], 0.9), ([[1, 2]], 0.9), ([1, 2], 1), ([1, 2], float("nan"))],
)
def test_bad_samples(losses, q):
    with pytest.raises(ValueError):
        fit_pot(np.array(losses), q)


@pytest.mark.parametrize(
    "overrides",
    [
        {"threshold_quantile": 0.999},
        {"sensitivity_quantiles": (0.9, 0.85)},
        {"sensitivity_quantiles": (0.9, 0.9)},
        {"minimum_exceedances": 1},
        {"bootstrap_replicates": 1},
        {"block_length": 0},
        {"seed": -1},
    ],
)
def test_bad_config(overrides):
    with pytest.raises(ValueError):
        EVTConfig(**overrides)


def test_bootstrap_preserves_blocks_repeats_and_does_not_hide_infinite_es():
    sequence = np.arange(40, dtype=float)
    sample = circular_block_sample(sequence, 5, np.random.default_rng(10))
    assert len(sample) == len(sequence)
    for block in sample.reshape(-1, 5):
        assert np.all(np.diff(block) % len(sequence) == 1)
    config = EVTConfig(bootstrap_replicates=20)
    losses = np.random.default_rng(9).exponential(0.01, 1000)
    draws = bootstrap_tail(losses, config, (0.95, 0.99))
    pd.testing.assert_frame_equal(draws, bootstrap_tail(losses, config, (0.95, 0.99)))
    assert not draws.equals(bootstrap_tail(losses, replace(config, seed=7), (0.95, 0.99)))
    point = pot_tail(fit_pot(losses, 0.9), 0.99)
    interval = bootstrap_intervals(draws, point)
    assert interval["var_ci_low"] < interval["var_ci_high"]
    assert interval["es_ci_low"] < interval["es_ci_high"]
    draws.loc[draws.index[-1], "es_fraction"] = None
    assert bootstrap_intervals(draws, point)["es_ci_high"] is None
    draws.loc[draws.confidence.eq(0.99), "var_fraction"] = None
    assert bootstrap_intervals(draws, point)["var_ci_high"] is None


def test_sensitivity_grid_does_not_replace_selected_threshold():
    config = EVTConfig()
    sample = np.random.default_rng(4).exponential(0.01, 1000)
    fits = threshold_diagnostics(sample, config)
    assert tuple(f.quantile for f in fits) == config.sensitivity_quantiles
    assert fits[-1].status == "insufficient_exceedances"
    assert config.threshold_quantile == 0.9


def test_boundary_bootstrap_does_not_hide_tied_sample_domain_failures():
    losses = np.random.default_rng(9).exponential(0.01, 1000)
    point = pot_tail(fit_pot(losses, 0.9), 0.9)
    assert point.status == "ok"
    draws = bootstrap_tail(losses, EVTConfig(bootstrap_replicates=20), (0.9,))
    assert draws.status.eq("below_tail_domain").any()
    assert draws.loc[draws.status.eq("below_tail_domain"), "var_fraction"].isna().all()
    interval = bootstrap_intervals(draws, point)
    assert interval["var_valid_replicates"] < 18
    assert interval["var_ci_low"] is None
    assert interval["es_ci_high"] is None


def test_pipeline_provenance_units_repeatability_future_exclusion_and_failure(tmp_path):
    snapshot = tmp_path / "data/snapshots/test"
    snapshot.mkdir(parents=True)
    (snapshot / "manifest.json").write_text("{}")
    data_output = tmp_path / "inputs"
    data_output.mkdir()
    rng = np.random.default_rng(123)
    panel = pd.DataFrame(
        rng.normal(0.0002, 0.01, (1800, 7)),
        columns=UNIVERSE,
        index=pd.bdate_range("2014-01-02", periods=1800),
    )
    panel.to_csv(data_output / "simple_returns.csv", index_label="Date")
    pd.DataFrame({"simple_return": 0.00001}, index=panel.index).to_csv(
        data_output / "risk_free_returns.csv", index_label="Date"
    )
    builder = lambda root, snapshot: data_output
    risk = RiskConfig(
        as_of=str(panel.index[1600].date()), simulations=1000, confidence_levels=(0.90, 0.95, 0.99)
    )
    config = EVTConfig(bootstrap_replicates=20)
    output = build_evt(tmp_path, snapshot, risk, config, data_builder=builder)
    estimates = pd.read_csv(output / "evt_estimates.csv")
    assert len(estimates) == 9
    boundary = estimates.loc[np.isclose(estimates.confidence, 0.90)]
    assert boundary.status.eq("ok").all()
    assert np.allclose(boundary.var_fraction, boundary.threshold)
    assert boundary.warning.str.contains("Threshold-boundary").all()
    available = estimates.loc[estimates.status.eq("ok")]
    assert len(available) == 9
    assert np.allclose(available.var_usd, available.var_fraction * 10_000_000)
    assert np.allclose(available.es_percent, available.es_fraction * 100)
    assert len(pd.read_csv(output / "risk_comparison.csv")) == 36
    diagnostics = pd.read_csv(output / "threshold_diagnostics.csv")
    assert diagnostics.loc[diagnostics.period.eq("development"), "end"].max() < "2019-01-01"
    assert len(list(output.glob("*.png"))) == 6
    summary = json.loads((output / "summary.json").read_text())
    assert (
        summary["human_validation"]
        == "recorded separately in docs/final/06-evt/03-manual-evt-check.md"
    )
    assert (
        summary["threshold_approval"]
        == "recorded separately in docs/final/06-evt/03-manual-evt-check.md"
    )
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    # Future mutations must not alter fitting, diagnostics, selection or any result artifact.
    panel.iloc[1601:] = 500
    panel.to_csv(data_output / "simple_returns.csv", index_label="Date")
    assert build_evt(tmp_path, snapshot, risk, config, data_builder=builder) == output
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}
    bad_config = replace(config, block_length=1001)
    with pytest.raises(ValueError, match="block length"):
        build_evt(tmp_path, snapshot, risk, bad_config, data_builder=builder)
    statuses = [json.loads(p.read_text()) for p in (tmp_path / "output/evt").rglob("status.json")]
    assert {s["status"] for s in statuses} == {"complete", "failed"}
