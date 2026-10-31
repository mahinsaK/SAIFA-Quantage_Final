"""Independent variance recursion and target-date exclusion for dynamic risk."""

import exchange_calendars as xcals
import numpy as np
import pandas as pd
import pytest

from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.domain.research import GarchFit, ResearchConfig
from saifa.models.research.volatility import fit_garch, variance_path, volatility_experiment


def test_variance_recursion_uses_the_previous_shock():
    actual = variance_path(np.array([1.0, 2.0, 3.0]), 0.1, 0.2, 0.5, 2.0)
    assert actual == pytest.approx([2.0, 1.3, 1.55])
    changed = variance_path(np.array([1.0, 2.0, 100.0]), 0.1, 0.2, 0.5, 2.0)
    assert actual == pytest.approx(changed)  # Last shock affects NEXT variance only.
    with pytest.raises(ValueError):
        variance_path(np.array([1.0]), 0.1, 0.5, 0.5, 2.0)


def test_garch_fit_is_stationary_finite_and_reconciles_next_variance():
    rng = np.random.default_rng(14)
    r = np.empty(1000)
    variance = 0.0001
    for t in range(len(r)):
        r[t] = np.sqrt(variance) * rng.normal()
        variance = 0.000005 + 0.1 * r[t] ** 2 + 0.85 * variance
    fit = fit_garch(r)
    assert fit.omega > 0 and min(fit.alpha, fit.beta) >= 0 and fit.alpha + fit.beta < 1
    assert fit.next_variance > 0 and np.isfinite(fit.standardized_residuals).all()
    h = variance_path(
        (r - fit.mean) * 100, fit.omega * 10000, fit.alpha, fit.beta, float(np.var(r * 100))
    )
    expected = fit.omega + fit.alpha * (r[-1] - fit.mean) ** 2 + fit.beta * h[-1] / 10000
    assert fit.next_variance == pytest.approx(expected)
    with pytest.raises(ValueError, match="constant"):
        fit_garch(np.zeros(300))


@pytest.fixture
def risk_history():
    dates = xcals.get_calendar("XNYS", start="2018-01-01", end="2022-12-31").sessions.tz_localize(
        None
    )
    rng = np.random.default_rng(81)
    returns = pd.DataFrame(
        rng.normal(0.0001, 0.005, (len(dates), 7)), index=dates, columns=UNIVERSE
    )
    weights = pd.DataFrame([[0.4, 0, 0, 0.6, 0, 0, 0]], index=["baseline_40_60"], columns=UNIVERSE)
    policy = OptimisationConfig(
        development_end_exclusive="2021-01-01",
        validation_end_exclusive="2022-01-01",
        evaluation_end_exclusive="2023-01-01",
    )
    return returns, weights, policy, ResearchConfig(volatility_lookback=252)


def test_forecast_excludes_target_and_future_returns(risk_history, monkeypatch):
    returns, weights, policy, settings = risk_history
    monkeypatch.setattr(
        "saifa.models.research.volatility.fit_garch",
        lambda r: GarchFit(0.0, 1e-5, 0.1, 0.8, 0.0001, (-2.0, -1.0, 0.0, 1.0, 2.0), "test"),
    )
    original, fits, corr = volatility_experiment(returns, weights, policy, settings)
    target = pd.Timestamp("2021-01-04")
    changed_returns = returns.copy()
    changed_returns.loc[target] += 0.05
    changed, _, changed_corr = volatility_experiment(changed_returns, weights, policy, settings)
    original_row = original.loc[original.forecast_date == str(target.date())]
    changed_row = changed.loc[changed.forecast_date == str(target.date())]
    assert original_row.var_fraction.to_numpy() == pytest.approx(
        changed_row.var_fraction.to_numpy()
    )
    assert original_row.es_fraction.to_numpy() == pytest.approx(changed_row.es_fraction.to_numpy())
    assert not np.allclose(original_row.loss_fraction, changed_row.loss_fraction)
    firstcorr = corr.loc[corr.forecast_date == str(target.date())]
    pd.testing.assert_frame_equal(
        firstcorr, changed_corr.loc[changed_corr.forecast_date == str(target.date())]
    )
    before = original.query(
        "forecast_date == '2021-01-05' and method == 'ewma_normal'"
    ).var_fraction
    after = changed.query("forecast_date == '2021-01-05' and method == 'ewma_normal'").var_fraction
    assert not np.allclose(before, after)
    assert (
        pd.to_datetime(fits.training_end)
        < pd.to_datetime(fits.execution_year.astype(str) + "-01-04")
    ).all()
    assert (original.parameter_fit_end <= original.as_of).all()
    # Empirical standardized-loss 95% VaR is 2, rescaled by the initial sigma .01.
    assert original_row.query("method == 'garch_fhs' and confidence == .95").var_fraction.iloc[
        0
    ] == pytest.approx(0.02)


def test_failed_garch_keeps_missing_forecasts_and_does_not_substitute(risk_history, monkeypatch):
    returns, weights, policy, settings = risk_history

    def failed(*args):
        raise RuntimeError("test convergence failure")

    monkeypatch.setattr("saifa.models.research.volatility.fit_garch", failed)
    frame, fits, _ = volatility_experiment(returns, weights, policy, settings)
    assert fits.status.eq("unavailable").all()
    garch = frame.loc[frame.method != "ewma_normal"]
    assert garch.var_fraction.isna().all() and garch.exception.isna().all()
    assert frame.loc[frame.method == "ewma_normal"].var_fraction.notna().all()
