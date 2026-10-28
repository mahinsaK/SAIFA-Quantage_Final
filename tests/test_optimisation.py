"""Focused checks for constrained construction and performance ratios."""

import numpy as np
import pandas as pd
import pytest

from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.models.optimisation import (
    annualised_inputs,
    efficient_frontier,
    optimise_portfolio,
    validate_policy_weights,
)
from saifa.models.performance import performance_ratios


def synthetic_inputs() -> tuple[pd.Series, pd.DataFrame]:
    means = pd.Series([0.08, 0.07, 0.09, 0.035, 0.045, 0.075, 0.10], index=UNIVERSE)
    volatilities = np.array([0.16, 0.18, 0.22, 0.05, 0.12, 0.21, 0.23])
    covariance = pd.DataFrame(np.diag(volatilities**2), index=UNIVERSE, columns=UNIVERSE)
    return means, covariance


def test_annualised_inputs_match_hand_calculation():
    dates = pd.bdate_range("2024-01-01", periods=252)
    values = np.tile(np.arange(1, 8, dtype=float) / 100_000, (252, 1))
    returns = pd.DataFrame(values, index=dates, columns=UNIVERSE)
    means, covariance = annualised_inputs(returns, 252)
    assert means["SPY"] == pytest.approx(0.00252)
    assert covariance.to_numpy() == pytest.approx(np.zeros((7, 7)), abs=1e-18)


def test_policy_validation_accepts_baseline_and_rejects_excess_equity():
    config = OptimisationConfig()
    baseline = pd.Series([0.4, 0, 0, 0.6, 0, 0, 0], index=UNIVERSE, dtype=float)
    validate_policy_weights(baseline, config)
    invalid = pd.Series([0.5, 0.1, 0, 0.4, 0, 0, 0], index=UNIVERSE, dtype=float)
    with pytest.raises(ValueError, match="Total-equity"):
        validate_policy_weights(invalid, config)


@pytest.mark.parametrize("name", ["minimum_volatility", "maximum_sharpe"])
def test_optimised_candidates_are_feasible(name):
    means, covariance = synthetic_inputs()
    config = OptimisationConfig(frontier_points=5)
    result = optimise_portfolio(name, means, covariance, 0.02, config)
    assert result.success
    validate_policy_weights(result.weights, config)
    assert result.volatility > 0
    assert np.isfinite(result.sharpe)


def test_efficient_frontier_is_feasible_and_ordered():
    means, covariance = synthetic_inputs()
    config = OptimisationConfig(frontier_points=7)
    frontier = efficient_frontier(means, covariance, 0.02, config)
    assert len(frontier) >= 3
    assert frontier.target_return.is_monotonic_increasing
    for _, row in frontier.iterrows():
        weights = pd.Series({ticker: row[f"weight_{ticker}"] for ticker in UNIVERSE})
        validate_policy_weights(weights, config)


def test_performance_ratios_match_direct_capm_and_drawdown_calculations():
    dates = pd.bdate_range("2024-01-01", periods=5)
    market = pd.Series([0.01, -0.02, 0.015, -0.01, 0.02], index=dates)
    risk_free = pd.Series(0.0001, index=dates)
    portfolio = risk_free + 0.5 * (market - risk_free)
    benchmark = pd.Series([0.004, -0.006, 0.006, -0.003, 0.008], index=dates)
    result = performance_ratios(portfolio, market, risk_free, benchmark)
    assert result["beta"] == pytest.approx(0.5)
    assert result["jensen_alpha"] == pytest.approx(0.0, abs=1e-12)
    wealth = (1 + portfolio).cumprod()
    assert result["maximum_drawdown"] == pytest.approx((wealth / wealth.cummax() - 1).min())


def test_performance_ratios_reject_misaligned_short_samples():
    one = pd.Series([0.01], index=pd.to_datetime(["2024-01-01"]))
    with pytest.raises(ValueError, match="three aligned"):
        performance_ratios(one, one, one, one)
