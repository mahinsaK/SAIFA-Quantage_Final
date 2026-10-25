"""Hand-checkable accounting identities and portfolio failure cases."""

import numpy as np
import pandas as pd
import pytest

from saifa.domain.config import BaselinePortfolioConfig
from saifa.domain.portfolio import PortfolioRun
from saifa.models.portfolio import (
    complete_month_ends,
    initial_allocation,
    performance_metrics,
    rebalance,
    simulate_portfolio,
)


def test_baseline_config_is_40_60_and_10_bps():
    config = BaselinePortfolioConfig()
    assert config.tickers == ("SPY", "AGG")
    assert config.weights == (0.4, 0.6)
    assert config.transaction_cost_rate == pytest.approx(0.001)


def test_initial_purchase_is_funded_including_cost():
    result = initial_allocation(100, np.array([0.4, 0.6]), 0.001)
    assert result.nav_after == pytest.approx(100 / 1.001)
    assert result.gross_traded == pytest.approx(result.nav_after)
    assert result.cost == pytest.approx(100 - result.nav_after)
    assert sum(result.values) + result.cost == pytest.approx(100)
    assert result.values[0] / result.nav_after == pytest.approx(0.4)


def test_hand_example_drift_and_exact_costed_rebalance():
    # Start with $40 SPY / $60 AGG. SPY rises 10%, AGG is flat: $44 + $60 = $104.
    pre = np.array([44.0, 60.0])
    weights = np.array([0.4, 0.6])
    result = rebalance(pre, weights, 0.001)
    assert pre[0] / pre.sum() == pytest.approx(44 / 104)
    assert result.nav_after == pytest.approx(103.99520095980804)
    assert result.values == pytest.approx((41.59808038392322, 62.39712057588482))
    assert result.trades == pytest.approx((-2.40191961607678, 2.39712057588482))
    assert result.gross_traded == pytest.approx(4.79904019196160)
    assert result.cost == pytest.approx(0.00479904019196160)
    assert sum(result.trades) == pytest.approx(-result.cost)
    assert result.nav_after + result.cost == pytest.approx(result.nav_before)


def test_two_day_portfolio_matches_hand_calculation_without_cost():
    dates = pd.to_datetime(["2024-01-30", "2024-01-31"])
    prices = pd.DataFrame({"SPY": [100, 110], "AGG": [100, 100]}, index=dates)
    run = simulate_portfolio(
        prices,
        pd.Series({"SPY": 0.4, "AGG": 0.6}),
        100,
        0,
        [dates[-1]],
        "manual",
    )
    assert run.daily.loc[dates[-1], "pre_trade_nav"] == pytest.approx(104)
    assert run.daily.loc[dates[-1], "daily_return"] == pytest.approx(0.04)
    assert run.daily.loc[dates[-1], "SPY_weight"] == pytest.approx(0.4)
    assert run.daily.loc[dates[-1], "AGG_weight"] == pytest.approx(0.6)
    assert run.transactions.iloc[-1].SPY_trade == pytest.approx(-2.4)
    assert run.transactions.iloc[-1].AGG_trade == pytest.approx(2.4)


def test_buy_and_hold_weights_drift_without_trades():
    dates = pd.to_datetime(["2024-01-30", "2024-01-31"])
    prices = pd.DataFrame({"SPY": [100, 110], "AGG": [100, 100]}, index=dates)
    run = simulate_portfolio(prices, pd.Series({"SPY": 0.4, "AGG": 0.6}), 100, 0, [], "hold")
    assert run.daily.iloc[-1].SPY_weight == pytest.approx(44 / 104)
    assert len(run.transactions) == 1


def test_future_prices_cannot_change_earlier_portfolio_values():
    dates = pd.date_range("2024-01-29", periods=4, freq="B")
    first = pd.DataFrame({"SPY": [100, 110, 90, 95], "AGG": [100, 100, 101, 102]}, index=dates)
    second = first.copy()
    second.iloc[-1] = [1_000, 1]
    args = (pd.Series({"SPY": 0.4, "AGG": 0.6}), 100, 0, [dates[2]], "monthly")
    run_one = simulate_portfolio(first, *args)
    run_two = simulate_portfolio(second, *args)
    pd.testing.assert_frame_equal(run_one.daily.iloc[:-1], run_two.daily.iloc[:-1])
    pd.testing.assert_frame_equal(run_one.transactions, run_two.transactions)


def test_complete_month_ends_excludes_truncated_last_month():
    observed = pd.to_datetime(["2024-01-30", "2024-01-31", "2024-02-01", "2024-02-20"])
    calendar = pd.bdate_range("2024-01-01", "2024-03-05")
    result = complete_month_ends(observed, calendar)
    assert list(result) == [pd.Timestamp("2024-01-31")]


def test_metrics_use_initial_capital_and_opening_high_water():
    dates = pd.to_datetime(["2024-01-01", "2024-07-02", "2025-01-01"])
    middle = 99 * (90 / 99) ** 0.5
    daily = pd.DataFrame(
        {
            "nav": [99.0, middle, 90.0],
            "daily_return": [-0.01, middle / 99 - 1, 90 / middle - 1],
            "drawdown": [-0.01, middle / 100 - 1, -0.10],
        },
        index=dates,
    )
    transactions = pd.DataFrame(
        {"transaction_cost": [1.0], "gross_traded": [99.0], "event": ["initial_allocation"]},
        index=dates[:1],
    )
    metrics = performance_metrics(PortfolioRun("test", daily, transactions), 100, 252)
    assert metrics["cumulative_return"] == pytest.approx(-0.10)
    assert metrics["annualised_return"] == pytest.approx(-0.10, abs=0.0003)
    assert metrics["maximum_drawdown"] == pytest.approx(-0.10)
    assert metrics["annualised_volatility"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    "prices",
    [
        pd.DataFrame({"SPY": [100, np.nan], "AGG": [100, 101]}),
        pd.DataFrame({"SPY": [100, 0], "AGG": [100, 101]}),
    ],
)
def test_invalid_prices_never_enter_portfolio(prices):
    prices.index = pd.to_datetime(["2024-01-01", "2024-01-02"])
    with pytest.raises(ValueError, match="finite and positive"):
        simulate_portfolio(prices, pd.Series({"SPY": 0.4, "AGG": 0.6}), 100, 0, [], "invalid")


def test_target_weights_must_match_price_assets():
    prices = pd.DataFrame(
        {"SPY": [100, 101], "AGG": [100, 101]},
        index=pd.to_datetime(["2024-01-01", "2024-01-02"]),
    )
    with pytest.raises(ValueError, match="match"):
        simulate_portfolio(prices, pd.Series({"SPY": 1.0}), 100, 0, [], "bad")
