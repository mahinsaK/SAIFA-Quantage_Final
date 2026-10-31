"""Independent withdrawal, inflation, joint-sample and simulation-event checks."""

import numpy as np
import pandas as pd
import pytest

from saifa.domain.config import UNIVERSE
from saifa.models.research.sustainability import (
    joint_monthly_inputs,
    monthly_factors,
    simulate_cashflows,
    wilson_interval,
)


def test_flat_two_year_cashflows_match_hand_calculation():
    factors = np.ones((20, 24))
    zero = np.zeros_like(factors)
    result, paths = simulate_cashflows(factors, zero, zero, 1000, 0, 0.03)
    assert paths[0, 0] == 1000 and paths[0, 12] == 970 and paths[0, 24] == 940
    assert result["mean_nominal_paid"] == 60 and result["ending_real_median"] == 940
    assert result["no_shortfall_fraction"] == 1
    assert result["conditional_wilson_low"] < 1  # Zero observed failures is not certainty.


def test_withdrawals_pay_sale_fee_and_index_relative_to_first_payment():
    one = np.ones((20, 12))
    zero = np.zeros_like(one)
    result, paths = simulate_cashflows(one, zero, zero, 1000, 0.01, 0.03)
    expected = 1000 / 1.01 - 30 / 0.99
    assert paths[0, -1] == pytest.approx(expected)
    assert result["mean_total_costs"] == pytest.approx(1000 - expected - 30)
    factors = np.ones((20, 24))
    fees = np.zeros_like(factors)
    inflation = np.full_like(factors, 1.1 ** (1 / 12) - 1)
    indexed, wealth = simulate_cashflows(factors, fees, inflation, 1000, 0, 0.03)
    assert indexed["mean_nominal_paid"] == pytest.approx(30 + 33)
    assert wealth[0, -1] == pytest.approx((1000 - 63) / 1.21)


def test_exhaustion_is_explicit_no_borrowing_and_no_automatic_recovery():
    factors = np.ones((20, 36))
    zero = np.zeros_like(factors)
    result, paths = simulate_cashflows(factors, zero, zero, 1000, 0, 0.9)
    assert result["no_shortfall_fraction"] == 0
    assert (paths[:, 24:] == 0).all()
    assert result["mean_nominal_paid"] == 1000
    assert result["conditional_wilson_high"] > 0


def test_vectorised_monthly_rebalance_matches_known_self_financing_example():
    # 40/60, first asset +10%, second flat; c=0.1% on gross buys+sells.
    net, fees = monthly_factors(np.array([[[0.1, 0.0]]]), np.array([0.4, 0.6]), 0.001)
    assert net[0, 0] == pytest.approx(1.0399520095980804)
    assert fees[0, 0] == pytest.approx(0.000047990401919616)
    assert net[0, 0] + fees[0, 0] == pytest.approx(1.04)


def test_missing_cpi_invalidates_both_adjacent_ratios_without_bridging():
    dates = pd.date_range("2022-01-31", periods=40, freq="ME")
    prices = pd.DataFrame(
        np.tile(100 * 1.01 ** np.arange(40)[:, None], (1, 7)), index=dates, columns=UNIVERSE
    )
    cpi = pd.Series(
        100 * 1.002 ** np.arange(40), index=pd.date_range("2022-01-01", periods=40, freq="MS")
    )
    cpi.loc["2023-02-01"] = np.nan
    joint = joint_monthly_inputs(prices, cpi)
    assert pd.Period("2023-02", "M") not in joint.index
    assert pd.Period("2023-03", "M") not in joint.index
    assert pd.Period("2023-04", "M") in joint.index
    assert len(joint) == 37
    assert joint.inflation.iloc[-1] == pytest.approx(0.002)


@pytest.mark.parametrize("count,total", [(0, 100), (100, 100), (50, 100)])
def test_conditional_intervals_are_bounded(count, total):
    low, high = wilson_interval(count, total)
    assert 0 <= low <= count / total <= high <= 1
    assert high > low


def test_invalid_scenarios_rejected():
    with pytest.raises(ValueError):
        monthly_factors(np.array([[[-1.1, 0]]]), np.array([0.4, 0.6]), 0.001)
    with pytest.raises(ValueError):
        simulate_cashflows(
            np.ones((2, 12)), np.zeros((2, 12)), np.full((2, 12), -1.0), 1000, 0, 0.03
        )
