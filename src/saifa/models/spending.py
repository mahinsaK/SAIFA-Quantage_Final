"""Proportional withdrawals layered on a verified, costed, monthly portfolio path.

Percentage costs and fractional holdings make the original strategy scale-invariant.
Proportional liquidation preserves its weights, so future net return factors are unchanged.
This identity does not cover fixed commissions, minimum lots, taxes or market impact.
"""

import numpy as np
import pandas as pd

from saifa.domain.decision import SpendingResult


def anniversary_payments(dates: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """First observed session on/after each anniversary; no final stub withdrawal."""
    dates = pd.DatetimeIndex(dates)
    if dates.empty or dates.has_duplicates or not dates.is_monotonic_increasing:
        raise ValueError("Payment dates require unique ordered observations")
    scheduled = []
    for year in range(1, dates[-1].year - dates[0].year + 1):
        anniversary = dates[0] + pd.DateOffset(years=year)
        position = dates.searchsorted(anniversary)
        if position < len(dates):
            scheduled.append(dates[position])
    return pd.DatetimeIndex(scheduled).unique()


def simulate_spending(
    daily: pd.DataFrame,
    initial_capital: float,
    cost_rate: float,
    inflation: float,
    withdrawal_rate: float = 0.03,
    objective: float = 0.03,
) -> SpendingResult:
    """Assumed inflation only; cash is paid after returns and scheduled rebalance.

    First annual payment is rate * original capital. Later payments grow with the
    assumed deflator relative to that first payment. Deflator=(1+inflation)^(days/365.25).
    Liquidating S pays (1-cost_rate)*S to the university. Shortfalls remain explicit.
    """
    frame = daily.copy()
    frame.index = pd.DatetimeIndex(frame.index)
    scalars = [initial_capital, cost_rate, inflation, withdrawal_rate, objective]
    if (
        not np.isfinite(scalars).all()
        or initial_capital <= 0
        or not 0 <= cost_rate < 1
        or inflation <= -1
        or withdrawal_rate < 0
        or objective <= -1
    ):
        raise ValueError("Invalid spending assumptions")
    if len(frame) < 2 or frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Spending needs at least two unique ordered dates")
    if not np.isfinite(frame[["nav", "transaction_cost"]]).all().all():
        raise ValueError("Missing NAV or cost; cannot simulate spending")
    if (frame.nav <= 0).any() or (frame.transaction_cost < 0).any():
        raise ValueError("NAV must be positive and costs nonnegative")
    if not np.isclose(frame.nav.iloc[0], initial_capital / (1 + cost_rate), rtol=1e-10):
        raise ValueError("Opening NAV does not match funded initial costs")
    scheduled = anniversary_payments(frame.index)
    years = (frame.index - frame.index[0]).days / 365.25
    deflator = pd.Series((1 + inflation) ** years, index=frame.index)
    first_deflator = deflator.loc[scheduled[0]] if len(scheduled) else 1.0
    nav = initial_capital
    previous_base = initial_capital
    rows, payments = [], []
    for i, (date, base) in enumerate(frame.iterrows()):
        scale = nav / previous_base
        pre = nav * base.nav / previous_base
        strategy_cost = initial_capital - base.nav if i == 0 else base.transaction_cost * scale
        requested = paid = sale = sale_cost = shortfall = 0.0
        if date in scheduled and withdrawal_rate:
            requested = initial_capital * withdrawal_rate * deflator.loc[date] / first_deflator
            paid = min(requested, pre * (1 - cost_rate))
            sale = paid / (1 - cost_rate)
            sale_cost = sale * cost_rate
            shortfall = max(0.0, requested - paid)
        nav = max(0.0, pre - sale)
        if not np.isclose(pre, nav + paid + sale_cost, atol=1e-7, rtol=1e-12):
            raise RuntimeError("Withdrawal is not self-financing")
        row = {
            "Date": date,
            "nav_before_withdrawal": pre,
            "nominal_nav": nav,
            "deflator": deflator.loc[date],
            "scenario_real_nav": nav / deflator.loc[date],
            "requested": requested,
            "paid": paid,
            "gross_sale": sale,
            "withdrawal_cost": sale_cost,
            "shortfall": shortfall,
            "strategy_cost": strategy_cost,
        }
        rows.append(row)
        if requested:
            payments.append(row.copy())
        previous_base = base.nav
    path = pd.DataFrame(rows)
    capital_growth = (nav / deflator.iloc[-1] / initial_capital) ** (1 / years[-1]) - 1
    no_spend_real = frame.nav.iloc[-1] / deflator.iloc[-1]
    summary = {
        "inflation_assumption": inflation,
        "withdrawal_rate": withdrawal_rate,
        "start_date": str(frame.index[0].date()),
        "end_date": str(frame.index[-1].date()),
        "ending_nominal_wealth": nav,
        "ending_scenario_real_wealth": nav / deflator.iloc[-1],
        "no_spending_nominal_wealth": float(frame.nav.iloc[-1]),
        "no_spending_scenario_real_wealth": no_spend_real,
        "annualised_real_remaining_capital_growth": capital_growth,
        "no_spending_real_capital_growth": (no_spend_real / initial_capital) ** (1 / years[-1]) - 1,
        "real_capital_objective": objective,
        "meets_after_spending_objective": bool(
            capital_growth >= objective and path.shortfall.sum() == 0
        ),
        "total_paid": float(path.paid.sum()),
        "total_real_paid": float((path.paid / path.deflator).sum()),
        "total_shortfall": float(path.shortfall.sum()),
        "payments": len(payments),
        "total_transaction_cost": float(path.strategy_cost.sum() + path.withdrawal_cost.sum()),
        "withdrawal_transaction_cost": float(path.withdrawal_cost.sum()),
        "status": "hypothetical_assumption",
    }
    return SpendingResult(path, pd.DataFrame(payments, columns=path.columns), summary)
