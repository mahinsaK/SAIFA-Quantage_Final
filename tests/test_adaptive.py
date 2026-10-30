"""Independent accounting, temporal leakage and failure checks for annual targets."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from saifa.domain.adaptive import AdaptiveConfig
from saifa.domain.config import UNIVERSE
from saifa.models.adaptive import annual_execution_dates, fit_annual_targets
from saifa.models.optimisation import validate_policy_weights
from saifa.models.portfolio import simulate_portfolio


@pytest.fixture(scope="module")
def history():
    dates = pd.bdate_range("2013-01-01", "2021-12-31")
    rng = np.random.default_rng(41)
    values = rng.normal(0.0003, 0.01, (len(dates), len(UNIVERSE)))
    values[:, 3] = rng.normal(0.0001, 0.003, len(dates))
    return pd.DataFrame(values, index=dates, columns=UNIVERSE), pd.Series(0.00005, index=dates)


def test_annual_training_is_trailing_and_strictly_before_execution(history):
    returns, rates = history
    dates = pd.to_datetime(["2019-01-02", "2020-01-02"])
    config = AdaptiveConfig()
    result = fit_annual_targets(dates, returns, rates, config)
    assert len(result) == 4
    assert set(result.training_start_inclusive) == {"2014-01-01", "2015-01-01"}
    assert (pd.to_datetime(result.training_end) < pd.to_datetime(result.execution_date)).all()
    for _, row in result.iterrows():
        validate_policy_weights(row.loc[list(UNIVERSE)].astype(float), config.portfolio)
        assert row.loc[list(UNIVERSE)].sum() == pytest.approx(1, abs=1e-14)
    changed = returns.copy()
    changed.loc[changed.index >= "2020-01-01"] += 0.02
    changed_rates = rates.copy()
    changed_rates.loc[changed_rates.index >= "2020-01-01"] = 0.5
    pd.testing.assert_frame_equal(result, fit_annual_targets(dates, changed, changed_rates, config))
    changed.loc[(changed.index >= "2019-01-01") & (changed.index < "2020-01-01"), "SPY"] += 0.01
    updated = fit_annual_targets(dates, changed, changed_rates, config)
    pd.testing.assert_frame_equal(result.iloc[:2], updated.iloc[:2])
    assert not np.allclose(result.expected_return.iloc[2:], updated.expected_return.iloc[2:])


def test_missing_training_rates_or_history_fails_instead_of_reusing_weights(history):
    returns, rates = history
    dates = pd.to_datetime(["2019-01-02"])
    with pytest.raises(ValueError, match="Insufficient"):
        fit_annual_targets(dates, returns.loc["2017":], rates, AdaptiveConfig())
    missing = rates.copy()
    missing.loc["2018-01-02"] = np.nan
    with pytest.raises(ValueError, match="risk-free"):
        fit_annual_targets(dates, returns, missing, AdaptiveConfig())
    # Four full years can exceed 1,000 observations but are not five calendar years.
    with pytest.raises(ValueError, match="coverage"):
        fit_annual_targets(dates, returns.loc["2015":], rates, AdaptiveConfig())


def test_solver_failure_is_explicit(history, monkeypatch):
    returns, rates = history
    monkeypatch.setattr(
        "saifa.models.adaptive.optimise_portfolio",
        lambda *args: SimpleNamespace(success=False, message="infeasible test"),
    )
    with pytest.raises(RuntimeError, match="infeasible test"):
        fit_annual_targets(pd.to_datetime(["2019-01-02"]), returns, rates, AdaptiveConfig())


def test_solver_roundoff_is_recorded_and_normalised(history, monkeypatch):
    returns, rates = history
    weights = pd.Series([0.2, 0, 0, 0.6, 0.2 - 1e-10, 0, 0], index=UNIVERSE)
    monkeypatch.setattr(
        "saifa.models.adaptive.optimise_portfolio",
        lambda name, *args: SimpleNamespace(
            success=True, message="test", name=name, weights=weights
        ),
    )
    result = fit_annual_targets(pd.to_datetime(["2019-01-02"]), returns, rates, AdaptiveConfig())
    assert result.solver_weight_sum.iloc[0] < 1
    assert result.loc[0, list(UNIVERSE)].sum() == pytest.approx(1, abs=1e-15)


def test_first_observed_session_per_year():
    dates = pd.to_datetime(["2019-01-02", "2019-12-31", "2020-01-02", "2020-01-03"])
    assert annual_execution_dates(dates).tolist() == [dates[0], dates[2]]
    with pytest.raises(ValueError):
        annual_execution_dates(dates[::-1])


@pytest.mark.parametrize("cost", [0.0, 0.01])
def test_old_holdings_earn_execution_day_return_and_new_targets_pay_cost(cost):
    dates = pd.to_datetime(["2019-12-30", "2019-12-31", "2020-01-02", "2020-01-03"])
    prices = pd.DataFrame({"A": [100, 100, 200, 200], "B": [100, 100, 100, 200]}, index=dates)
    initial = pd.Series({"A": 1.0, "B": 0.0})
    targets = pd.DataFrame([[1.0, 0.0], [0.0, 1.0]], index=dates[[0, 2]], columns=prices.columns)
    run = simulate_portfolio(
        prices, initial, 1000, cost, [dates[2]], "annual", target_schedule=targets
    )
    pre_trade = 1000 / (1 + cost) * 2
    post_trade = pre_trade * (1 - cost) / (1 + cost)
    assert run.daily.loc[dates[2], "pre_trade_nav"] == pytest.approx(pre_trade)
    assert run.daily.loc[dates[2], "nav"] == pytest.approx(post_trade)
    assert run.daily.iloc[-1].nav == pytest.approx(post_trade * 2)
    assert run.daily.loc[dates[1], "A_target"] == 1
    assert run.daily.loc[dates[2], "B_target"] == 1
    trades = run.transactions.loc[dates[2]]
    assert trades.event == "annual_reoptimisation"
    assert trades.A_trade + trades.B_trade + trades.transaction_cost == pytest.approx(0, abs=1e-10)
    assert trades.nav_before == pytest.approx(trades.nav_after + trades.transaction_cost)
    assert trades.gross_traded == pytest.approx(pre_trade + post_trade)
    assert len(run.transactions) == 2  # Coincident monthly/annual dates trade once.


def test_constant_schedule_reproduces_existing_engine():
    dates = pd.bdate_range("2020-01-02", periods=10)
    prices = pd.DataFrame({"A": np.arange(100.0, 110.0), "B": 100.0}, index=dates)
    weights = pd.Series({"A": 0.4, "B": 0.6})
    args = (prices, weights, 1000, 0.001, [dates[5]], "same")
    fixed = simulate_portfolio(*args)
    annual = simulate_portfolio(*args, target_schedule=weights.to_frame().T.set_axis(dates[:1]))
    pd.testing.assert_frame_equal(fixed.daily, annual.daily.loc[:, fixed.daily.columns])
    pd.testing.assert_frame_equal(fixed.transactions, annual.transactions)


@pytest.mark.parametrize(
    "failure", ["unknown_date", "duplicate", "wrong_initial", "nonunit", "missing_asset"]
)
def test_invalid_target_schedule_fails(failure):
    dates = pd.bdate_range("2020-01-02", periods=4)
    prices = pd.DataFrame({"A": 100.0, "B": 100.0}, index=dates)
    weights = pd.Series({"A": 0.4, "B": 0.6})
    targets = pd.DataFrame([[0.4, 0.6], [0.6, 0.4]], index=dates[[0, 2]], columns=prices.columns)
    if failure == "unknown_date":
        targets.index = pd.to_datetime(["2020-01-02", "2021-01-02"])
    elif failure == "duplicate":
        targets.index = dates[[0, 0]]
    elif failure == "wrong_initial":
        targets.iloc[0] = [0.5, 0.5]
    elif failure == "nonunit":
        targets.iloc[1] = [0.6, 0.6]
    else:
        targets = targets.drop(columns="B")
    with pytest.raises(ValueError):
        simulate_portfolio(prices, weights, 1000, 0.001, [], "bad", target_schedule=targets)


@pytest.mark.parametrize(
    "changes", [{"lookback_years": 0}, {"lookback_years": 1.5}, {"minimum_observations": 10}]
)
def test_invalid_experiment_configuration(changes):
    with pytest.raises(ValueError):
        replace(AdaptiveConfig(), **changes)
