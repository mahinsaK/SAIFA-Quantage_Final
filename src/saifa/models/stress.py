"""Complete-calendar buy-and-hold crisis replays and direct joint ETF shocks."""

from dataclasses import replace

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from saifa.domain.config import HistoricalStressPeriod
from saifa.domain.stress import HistoricalStressResult, ShockResult, ShockRun, StressRun
from saifa.models.risk import ordered_weights


def _nav_and_level(nav: float, level: float) -> None:
    if not np.isfinite(nav) or nav <= 0 or not np.isfinite(level) or not 0 < level < 1:
        raise ValueError("Positive finite NAV and review level in (0, 1) required")


def historical_replay(
    returns: pd.DataFrame,
    weights: pd.Series,
    period: HistoricalStressPeriod,
    nav: float,
    strategy: str,
    weights_as_of: str,
    review_level: float,
) -> StressRun:
    _nav_and_level(nav, review_level)
    index = returns.index
    if (
        not isinstance(index, pd.DatetimeIndex)
        or index.tz is not None
        or not index.is_unique
        or not index.is_monotonic_increasing
        or not index.equals(index.normalize())
    ):
        raise ValueError("Stress inputs need ordered unique naive session dates")
    if not returns.columns.is_unique:
        raise ValueError("Asset columns must be unique")
    w = ordered_weights(weights, returns.columns)
    calendar = xcals.get_calendar(
        "XNYS",
        start=pd.Timestamp(period.start) - pd.Timedelta(days=10),
        end=pd.Timestamp(period.end_exclusive) - pd.Timedelta(days=1),
    )
    sessions = calendar.sessions.tz_localize(None)
    expected = sessions[(sessions >= period.start) & (sessions < period.end_exclusive)]
    selected = returns.loc[(index >= period.start) & (index < period.end_exclusive)]
    base = HistoricalStressResult(
        strategy,
        period.name,
        period.start,
        period.end_exclusive,
        len(expected),
        len(selected),
        "unavailable",
        "",
        nav,
        weights_as_of,
    )
    if expected.empty or not selected.index.equals(expected):
        missing = expected.difference(selected.index).strftime("%Y-%m-%d").tolist()
        unexpected = selected.index.difference(expected).strftime("%Y-%m-%d").tolist()
        warning = f"Incomplete/invalid crisis calendar: missing={missing}; unexpected={unexpected}. No partial replay."
        return StressRun(replace(base, warning=warning), pd.DataFrame(), pd.DataFrame())
    values = selected.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < -1).any():
        return StressRun(
            replace(base, warning="Invalid or missing simple returns; no fill or deletion"),
            pd.DataFrame(),
            pd.DataFrame(),
        )
    base_date = sessions[sessions < expected[0]][-1]
    dates = pd.DatetimeIndex([base_date, *expected], name="Date")
    growth = np.vstack([np.ones(len(w)), np.cumprod(1 + values, axis=0)])
    holdings = growth * (nav * w)
    wealth = holdings.sum(axis=1)
    peak = np.maximum.accumulate(wealth)
    drawdown = (peak - wealth) / peak
    daily = np.zeros(len(wealth))
    # A bankrupt buy-and-hold portfolio stays at zero; its subsequent return is undefined.
    daily[1:] = (
        np.divide(
            wealth[1:], wealth[:-1], out=np.full(len(wealth) - 1, np.nan), where=wealth[:-1] > 0
        )
        - 1
    )
    path = pd.DataFrame(
        {
            "nav": wealth,
            "daily_return": daily,
            "cumulative_return": wealth / nav - 1,
            "loss_from_initial_usd": nav - wealth,
            "running_peak_nav": peak,
            "drawdown_fraction": drawdown,
        },
        index=dates,
    )
    for i, ticker in enumerate(returns.columns):
        path[f"{ticker}_value"] = holdings[:, i]
        path[f"{ticker}_weight"] = np.divide(
            holdings[:, i], wealth, out=np.full(len(wealth), np.nan), where=wealth > 0
        )
    trough = int(np.argmax(drawdown))
    peak_index = int(np.argmax(wealth[: trough + 1]))
    components = pd.DataFrame(
        {
            "ticker": returns.columns,
            "initial_weight": w,
            "asset_cumulative_return": growth[-1] - 1,
            "terminal_loss_fraction": -w * (growth[-1] - 1),
            "terminal_loss_usd": nav * w - holdings[-1],
        }
    )
    summary = replace(
        base,
        status="ok",
        warning="Retrospective fixed-initial-allocation replay; holdings drift. No trading costs, withdrawals or rebalancing. Not a historical investment track record.",
        base_date=str(base_date.date()),
        last_date=str(expected[-1].date()),
        weights_available_at_start=bool(pd.Timestamp(weights_as_of) <= base_date),
        terminal_return_fraction=float(wealth[-1] / nav - 1),
        terminal_loss_fraction=float(1 - wealth[-1] / nav),
        terminal_loss_usd=float(nav - wealth[-1]),
        worst_day_loss_fraction=float(-np.nanmin(daily[1:])),
        worst_loss_from_initial_usd=float(np.max(nav - wealth)),
        maximum_drawdown_fraction=float(drawdown[trough]),
        drawdown_usd_at_max_fraction=float(wealth[peak_index] - wealth[trough]),
        peak_date=str(dates[peak_index].date()),
        trough_date=str(dates[trough].date()),
        peak_nav=float(wealth[peak_index]),
        trough_nav=float(wealth[trough]),
        drawdown_review_level=review_level,
        review_trigger_breached=bool(drawdown[trough] > review_level),
    )
    return StressRun(summary, path, components)


def joint_shock(
    weights: pd.Series,
    shocks: pd.Series,
    nav: float,
    strategy: str,
    name: str,
    multiplier: float,
    review_level: float,
) -> ShockRun:
    _nav_and_level(nav, review_level)
    if not shocks.index.is_unique:
        raise ValueError("Each asset must have exactly one shock")
    w = ordered_weights(weights, shocks.index)
    if not np.isfinite(multiplier) or multiplier <= 0:
        raise ValueError("Positive finite severity multiplier required")
    changes = shocks.to_numpy(dtype=float) * multiplier
    if not np.isfinite(changes).all() or (changes < -1).any():
        raise ValueError("Scaled shocks must be finite simple returns >= -100%")
    losses = -w * changes
    total = float(losses.sum())
    return ShockRun(
        ShockResult(
            strategy,
            name,
            multiplier,
            1,
            nav,
            total,
            nav * total,
            review_level,
            bool(total > review_level),
        ),
        pd.DataFrame(
            {
                "ticker": shocks.index,
                "weight": w,
                "shock_return": changes,
                "loss_fraction": losses,
                "loss_usd": nav * losses,
            }
        ),
    )
