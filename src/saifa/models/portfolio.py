"""Self-financing buy-and-hold and periodic-rebalancing accounting."""

from collections.abc import Collection

import numpy as np
import pandas as pd

from saifa.domain.portfolio import PortfolioRun, RebalanceResult


def _validated_weights(weights: pd.Series, columns: pd.Index) -> np.ndarray:
    if set(weights.index) != set(columns):
        raise ValueError("Target weights must match the selected price columns")
    ordered = weights.reindex(columns).to_numpy(dtype=float)
    if not np.isfinite(ordered).all() or (ordered < 0).any() or not np.isclose(ordered.sum(), 1):
        raise ValueError("Target weights must be finite, nonnegative and sum to one")
    return ordered


def initial_allocation(
    initial_capital: float, weights: np.ndarray, cost_rate: float
) -> RebalanceResult:
    """Invest cash and charge cost on the gross purchases without borrowing."""
    if initial_capital <= 0 or not 0 <= cost_rate < 1:
        raise ValueError("Invalid initial capital or transaction-cost rate")
    invested = initial_capital / (1 + cost_rate)
    cost = initial_capital - invested
    values = weights * invested
    return RebalanceResult(
        values=tuple(values),
        trades=tuple(values),
        gross_traded=float(invested),
        cost=float(cost),
        nav_before=float(initial_capital),
        nav_after=float(invested),
    )


def rebalance(pre_values: np.ndarray, weights: np.ndarray, cost_rate: float) -> RebalanceResult:
    """Solve NAV after costs where cost applies to buys plus sells."""
    values = np.asarray(pre_values, dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or values.sum() <= 0:
        raise ValueError("Pre-trade asset values must be finite, nonnegative and funded")
    if not 0 <= cost_rate < 1:
        raise ValueError("Transaction-cost rate must be in [0, 1)")
    nav_before = float(values.sum())
    if cost_rate == 0:
        nav_after = nav_before
    else:
        # Unique self-financing root of x + c*sum(|w*x-v|) = pre-trade NAV.
        low, high = nav_before / (1 + cost_rate), nav_before
        for _ in range(100):
            mid = (low + high) / 2
            equation = mid + cost_rate * np.abs(weights * mid - values).sum() - nav_before
            if equation > 0:
                high = mid
            else:
                low = mid
        nav_after = (low + high) / 2
    post_values = weights * nav_after
    trades = post_values - values
    gross = float(np.abs(trades).sum())
    cost = float(cost_rate * gross)
    if not np.isclose(nav_after + cost, nav_before, rtol=1e-12, atol=1e-7):
        raise RuntimeError("Rebalance failed the self-financing identity")
    if not np.isclose(trades.sum(), -cost, rtol=1e-12, atol=1e-7):
        raise RuntimeError("Trades do not fund transaction cost")
    return RebalanceResult(
        values=tuple(post_values),
        trades=tuple(trades),
        gross_traded=gross,
        cost=cost,
        nav_before=nav_before,
        nav_after=float(nav_after),
    )


def simulate_portfolio(
    prices: pd.DataFrame,
    weights: pd.Series,
    initial_capital: float,
    cost_rate: float,
    rebalance_dates: Collection[pd.Timestamp],
    strategy: str,
) -> PortfolioRun:
    """Value holdings at each close, then execute any scheduled close trade."""
    if len(prices) < 2 or prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("Portfolio needs at least two unique, ordered price dates")
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError("Portfolio prices must be finite and positive")
    target = _validated_weights(weights, prices.columns)
    dates = prices.index
    unknown = set(pd.DatetimeIndex(rebalance_dates)) - set(dates[1:])
    if unknown:
        raise ValueError("Rebalance dates must be observed after the initial date")
    scheduled = set(pd.DatetimeIndex(rebalance_dates))
    allocation = initial_allocation(initial_capital, target, cost_rate)
    holdings = np.asarray(allocation.values)
    previous_nav = initial_capital
    rows, transactions = [], []

    def record_transaction(date, event, result):
        row = {
            "Date": date,
            "strategy": strategy,
            "event": event,
            "nav_before": result.nav_before,
            "nav_after": result.nav_after,
            "gross_traded": result.gross_traded,
            "transaction_cost": result.cost,
        }
        row.update(
            {f"{ticker}_trade": trade for ticker, trade in zip(prices.columns, result.trades)}
        )
        transactions.append(row)

    record_transaction(dates[0], "initial_allocation", allocation)
    high_water = initial_capital
    for position, date in enumerate(dates):
        if position:
            price_ratio = prices.iloc[position].to_numpy() / prices.iloc[position - 1].to_numpy()
            holdings *= price_ratio
        pre_trade_nav = float(holdings.sum())
        is_rebalance = date in scheduled
        cost = gross = 0.0
        if is_rebalance:
            result = rebalance(holdings, target, cost_rate)
            holdings = np.asarray(result.values)
            cost, gross = result.cost, result.gross_traded
            record_transaction(date, "scheduled_rebalance", result)
        nav = float(holdings.sum())
        daily_return = nav / previous_nav - 1
        high_water = max(high_water, nav)
        row = {
            "Date": date,
            "strategy": strategy,
            "nav": nav,
            "daily_return": daily_return,
            "cumulative_return": nav / initial_capital - 1,
            "drawdown": nav / high_water - 1,
            "pre_trade_nav": pre_trade_nav,
            "gross_traded": gross,
            "transaction_cost": cost,
            "rebalanced": is_rebalance,
        }
        row.update({f"{ticker}_value": value for ticker, value in zip(prices.columns, holdings)})
        row.update(
            {f"{ticker}_weight": value / nav for ticker, value in zip(prices.columns, holdings)}
        )
        rows.append(row)
        previous_nav = nav
    return PortfolioRun(
        strategy=strategy,
        daily=pd.DataFrame(rows).set_index("Date"),
        transactions=pd.DataFrame(transactions).set_index("Date"),
    )


def complete_month_ends(
    dates: pd.DatetimeIndex, calendar_sessions: pd.DatetimeIndex
) -> pd.DatetimeIndex:
    """Observed dates that are true calendar month-ends; exclude a truncated final month."""
    if dates.empty or not dates.is_unique or not dates.is_monotonic_increasing:
        raise ValueError("Dates must be nonempty, unique and ordered")
    sessions = pd.DatetimeIndex(calendar_sessions).tz_localize(None)
    session_frame = pd.DataFrame(index=sessions)
    actual_month_ends = session_frame.groupby(sessions.to_period("M")).tail(1).index
    result = dates.intersection(actual_month_ends)
    return result[result > dates[0]]


def performance_metrics(
    run: PortfolioRun, initial_capital: float, annual_trading_days: int
) -> dict[str, float | int | str]:
    daily = run.daily
    elapsed_days = (daily.index[-1] - daily.index[0]).days
    if elapsed_days <= 0:
        raise ValueError("Annualised metrics need a positive elapsed period")
    terminal = float(daily.nav.iloc[-1])
    market_returns = daily.daily_return.iloc[1:]
    cumulative = terminal / initial_capital - 1
    annualised = (terminal / initial_capital) ** (365.25 / elapsed_days) - 1
    volatility = float(market_returns.std(ddof=1) * np.sqrt(annual_trading_days))
    return {
        "strategy": run.strategy,
        "start_date": daily.index[0].date().isoformat(),
        "end_date": daily.index[-1].date().isoformat(),
        "observations": len(daily),
        "initial_capital": initial_capital,
        "ending_value": terminal,
        "cumulative_return": cumulative,
        "annualised_return": annualised,
        "annualised_volatility": volatility,
        "maximum_drawdown": float(daily.drawdown.min()),
        "total_transaction_cost": float(run.transactions.transaction_cost.sum()),
        "total_gross_traded": float(run.transactions.gross_traded.sum()),
        "scheduled_rebalances": int((run.transactions.event == "scheduled_rebalance").sum()),
    }
