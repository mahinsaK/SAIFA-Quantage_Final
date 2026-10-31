"""Fee homogeneity, prior volume and income proxies must retain their actual scope."""

import numpy as np
import pandas as pd
import pytest

from saifa.models.portfolio import rebalance, simulate_portfolio
from saifa.models.research.implementation import fee_overlay, income_proxy, liquidity_proxy


def test_complete_rotation_pays_both_sides_of_transaction_cost():
    result = rebalance(np.array([1000.0, 0.0]), np.array([0.0, 1.0]), 0.01)
    expected = 1000 * 0.99 / 1.01
    assert result.nav_after == pytest.approx(expected)
    assert result.gross_traded == pytest.approx(1000 + expected)
    assert result.nav_after + result.cost == pytest.approx(1000)


def test_extra_fee_is_a_proportional_charge_and_preserves_trade_funding():
    dates = pd.to_datetime(["2021-01-01", "2022-01-01"])
    prices = pd.DataFrame({"A": [100.0, 100.0], "B": [100.0, 100.0]}, index=dates)
    run = simulate_portfolio(prices, pd.Series({"A": 0.4, "B": 0.6}), 1000, 0, [], "test")
    charged = fee_overlay(run, 1000, 500)
    expected = 1000 * np.exp(-0.05 * 365 / 365.25)
    assert charged.daily.nav.iloc[-1] == pytest.approx(expected)
    assert charged.daily.additional_fee.sum() == pytest.approx(1000 - expected)
    assert run.daily.nav.iloc[-1] == 1000  # Inputs were not mutated.
    nofee = fee_overlay(run, 1000, 0)
    pd.testing.assert_series_equal(nofee.daily.nav, run.daily.nav)
    assert np.allclose(
        charged.transactions.nav_before,
        charged.transactions.nav_after + charged.transactions.transaction_cost,
    )


def test_volume_proxy_does_not_use_execution_day_volume():
    dates = pd.bdate_range("2020-01-01", periods=25)
    raw = pd.DataFrame({"Close": 100.0, "Volume": 10.0}, index=dates)
    trades = pd.DataFrame({"strategy": "test", "A_trade": 100.0}, index=dates[-1:])
    before = liquidity_proxy(trades, {"A": raw})
    raw.loc[dates[-1], "Volume"] = 1e9
    after = liquidity_proxy(trades, {"A": raw})
    assert before.participation_proxy.iloc[0] == pytest.approx(0.1)
    pd.testing.assert_frame_equal(before, after)


def test_fee_overlay_matches_independent_holdings_replay_with_rebalancing():
    dates = pd.to_datetime(["2021-01-04", "2021-06-30", "2021-12-31"])
    prices = pd.DataFrame({"A": [100.0, 110.0, 105.0], "B": [100.0, 95.0, 98.0]}, index=dates)
    weights = pd.Series({"A": 0.4, "B": 0.6})
    capital = 1000.0
    cost = 0.001
    base = simulate_portfolio(prices, weights, capital, cost, dates[1:], "test")
    overlay = fee_overlay(base, capital, 500)
    holdings = weights.to_numpy() * capital / (1 + cost)
    values = [holdings.sum()]
    fee_total = 0.0
    trade_cost = capital - holdings.sum()
    for i in range(1, len(dates)):
        holdings *= prices.iloc[i].to_numpy() / prices.iloc[i - 1].to_numpy()
        fee = holdings.sum() * (1 - np.exp(-0.05 * (dates[i] - dates[i - 1]).days / 365.25))
        holdings *= np.exp(-0.05 * (dates[i] - dates[i - 1]).days / 365.25)
        result = rebalance(holdings, weights.to_numpy(), cost)
        holdings = np.asarray(result.values)
        fee_total += fee
        trade_cost += result.cost
        values.append(holdings.sum())
    assert overlay.daily.nav.to_numpy() == pytest.approx(values)
    assert overlay.daily.additional_fee.sum() == pytest.approx(fee_total)
    assert overlay.transactions.transaction_cost.sum() == pytest.approx(trade_cost)


def test_income_proxy_uses_prior_close_and_excludes_allocation_day():
    dates = pd.bdate_range("2022-01-03", periods=4)
    raw = pd.DataFrame(
        {
            "Close": [100.0, 105.0, 105.0, 105.0],
            "Dividends": [10.0, 1.0, 0.0, 0.0],
            "Capital Gains": 0.0,
            "Stock Splits": 0.0,
        },
        index=dates,
    )
    weights = pd.DataFrame({"A": [1.0]}, index=["test"])
    summary, ledger = income_proxy(
        {"A": raw}, weights, str(dates[0].date()), str(dates[-1].date()), 1000
    )
    assert summary.distribution_proxy_usd.iloc[0] == 10
    assert summary.partial_eligible_proxy_usd.iloc[0] == 10
    assert summary.covered_target_weight.iloc[0] == 1
    assert summary.status.iloc[0] == "proxy_only"
    assert ledger.ex_date.iloc[0] == str(dates[1].date())
    raw.loc[dates[-1], "Stock Splits"] = 2
    unavailable, _ = income_proxy(
        {"A": raw}, weights, str(dates[0].date()), str(dates[-1].date()), 1000
    )
    assert unavailable.status.iloc[0] == "unavailable"
    assert np.isnan(unavailable.distribution_proxy_usd.iloc[0])
    assert np.isnan(unavailable.partial_eligible_proxy_usd.iloc[0])
    assert unavailable.covered_target_weight.iloc[0] == 0
    assert "split" in unavailable.reason.iloc[0]


def test_income_proxy_keeps_valid_asset_evidence_without_claiming_a_complete_total():
    dates = pd.bdate_range("2022-01-03", periods=3)
    eligible = pd.DataFrame(
        {
            "Close": [100.0, 100.0, 100.0],
            "Dividends": [0.0, 1.0, 0.0],
            "Capital Gains": 0.0,
            "Stock Splits": 0.0,
        },
        index=dates,
    )
    split = eligible.copy()
    split.loc[dates[-1], "Stock Splits"] = 2
    weights = pd.DataFrame({"A": [0.6], "B": [0.4]}, index=["test"])
    summary, ledger = income_proxy(
        {"A": eligible, "B": split},
        weights,
        str(dates[0].date()),
        str(dates[-1].date()),
        1000,
    )
    row = summary.iloc[0]
    assert row.status == "unavailable"
    assert np.isnan(row.distribution_proxy_usd)
    assert row.partial_eligible_proxy_usd == pytest.approx(6.0)
    assert row.covered_target_weight == pytest.approx(0.6)
    assert row.covered_assets == "A"
    assert ledger.ticker.tolist() == ["A"]
