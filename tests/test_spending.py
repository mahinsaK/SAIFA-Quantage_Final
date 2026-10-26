"""Independent cash-flow examples and scale-invariance checks."""

import numpy as np
import pandas as pd
import pytest

from saifa.models.portfolio import initial_allocation, rebalance, simulate_portfolio
from saifa.models.spending import anniversary_payments, simulate_spending


def flat_path(cost=0.0):
    dates = pd.to_datetime(["2022-01-03", "2023-01-03", "2024-01-03"])
    return pd.DataFrame({"nav": 1000 / (1 + cost), "transaction_cost": 0.0}, index=dates)


def test_flat_two_payments_and_no_invented_returns():
    result = simulate_spending(flat_path(), 1000, 0, 0)
    assert result.payments.paid.tolist() == [30, 30]
    assert result.daily.nominal_nav.tolist() == [1000, 970, 940]
    assert result.summary["total_paid"] == 60
    assert not result.summary["meets_after_spending_objective"]


def test_withdrawal_sell_cost_is_funded_from_portfolio():
    result = simulate_spending(flat_path(0.01), 1000, 0.01, 0)
    payment = result.payments.iloc[0]
    assert payment.gross_sale == pytest.approx(30 / 0.99)
    assert payment.withdrawal_cost == pytest.approx(0.30303030303)
    assert payment.nominal_nav == pytest.approx(1000 / 1.01 - 30 / 0.99)
    assert np.allclose(
        result.daily.nav_before_withdrawal,
        result.daily.nominal_nav + result.daily.paid + result.daily.withdrawal_cost,
    )


def test_subsequent_payments_indexed_and_real_wealth_deflated():
    result = simulate_spending(flat_path(), 1000, 0, 0.10)
    factor = 1.10 ** (365 / 365.25)
    assert result.payments.paid.tolist() == pytest.approx([30, 30 * factor])
    assert result.summary["ending_scenario_real_wealth"] == pytest.approx(
        (1000 - 30 - 30 * factor) / 1.10 ** (730 / 365.25)
    )
    assert result.summary["no_spending_scenario_real_wealth"] == pytest.approx(
        1000 / 1.10 ** (730 / 365.25)
    )


def test_payment_on_first_observed_anniversary_session_no_stub():
    dates = pd.to_datetime(["2022-01-03", "2022-12-30", "2023-01-04", "2023-10-22"])
    assert anniversary_payments(dates).tolist() == [pd.Timestamp("2023-01-04")]
    assert anniversary_payments(dates[:2]).empty


def test_insufficient_funds_do_not_borrow_or_hide_shortfall():
    result = simulate_spending(flat_path(0.01), 1000, 0.01, 0, withdrawal_rate=1)
    assert result.daily.nominal_nav.iloc[-1] == 0
    assert result.payments.shortfall.iloc[0] > 0
    assert result.payments.shortfall.iloc[1] == 1000
    assert result.payments.paid.iloc[1] == 0


def test_no_spending_recovers_original_nav_and_costs():
    dates = pd.to_datetime(["2022-01-03", "2023-01-03", "2024-01-03"])
    prices = pd.DataFrame({"A": [100, 140, 120], "B": [100, 95, 110]}, index=dates)
    run = simulate_portfolio(
        prices, pd.Series({"A": 0.4, "B": 0.6}), 1000, 0.001, dates[1:], "test"
    )
    result = simulate_spending(run.daily, 1000, 0.001, 0.02, withdrawal_rate=0)
    assert np.allclose(result.daily.nominal_nav, run.daily.nav)
    assert result.summary["total_transaction_cost"] == pytest.approx(
        run.transactions.transaction_cost.sum()
    )


def test_scaled_path_matches_independent_holdings_with_same_day_rebalance():
    dates = pd.to_datetime(
        ["2022-01-03", "2022-12-30", "2023-01-03", "2023-01-31", "2024-01-03", "2024-02-01"]
    )
    prices = pd.DataFrame(
        {"A": [100, 80, 90, 95, 120, 110], "B": [100, 105, 103, 106, 108, 115]}, index=dates
    )
    targets = np.array([0.4, 0.6])
    scheduled = dates[1:-1]
    run = simulate_portfolio(
        prices, pd.Series(targets, index=prices.columns), 1000, 0.001, scheduled, "test"
    )
    result = simulate_spending(run.daily, 1000, 0.001, 0)
    opening = initial_allocation(1000, targets, 0.001)
    holdings = np.asarray(opening.values)
    expected = [holdings.sum()]
    costs = opening.cost
    for i, date in enumerate(dates[1:], 1):
        holdings *= prices.iloc[i].to_numpy() / prices.iloc[i - 1].to_numpy()
        if date in scheduled:
            trade = rebalance(holdings, targets, 0.001)
            holdings = np.asarray(trade.values)
            costs += trade.cost
        if date in (pd.Timestamp("2023-01-03"), pd.Timestamp("2024-01-03")):
            sale = 30 / 0.999
            holdings *= 1 - sale / holdings.sum()
            costs += sale * 0.001
        expected.append(holdings.sum())
    assert np.allclose(result.daily.nominal_nav, expected)
    assert result.summary["total_transaction_cost"] == pytest.approx(costs)


@pytest.mark.parametrize("field,value", [("nav", np.nan), ("nav", -1), ("transaction_cost", -1)])
def test_invalid_input_rejected(field, value):
    path = flat_path()
    path.iloc[1, path.columns.get_loc(field)] = value
    with pytest.raises(ValueError):
        simulate_spending(path, 1000, 0, 0)


@pytest.mark.parametrize(
    "cost,inflation,rate", [(1, 0, 0.03), (0, -1, 0.03), (0, 0, -1), (0, np.nan, 0.03)]
)
def test_invalid_assumptions_rejected(cost, inflation, rate):
    with pytest.raises(ValueError):
        simulate_spending(flat_path(), 1000, cost, inflation, rate)


def test_initial_cost_basis_mismatch_rejected():
    with pytest.raises(ValueError, match="Opening NAV"):
        simulate_spending(flat_path(), 1000, 0.01, 0)
