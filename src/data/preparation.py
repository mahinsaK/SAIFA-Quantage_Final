"""Calendar alignment and return calculations without network or file access."""

from dataclasses import dataclass

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from src.domain.config import DataConfig


@dataclass(frozen=True)
class PriceAudit:
    prices: pd.DataFrame
    flags: pd.DataFrame
    coverage: pd.DataFrame


def trading_sessions(config: DataConfig) -> pd.DatetimeIndex:
    end = pd.Timestamp(config.end_exclusive) - pd.Timedelta(days=1)
    calendar = xcals.get_calendar(config.calendar, start=config.start, end=end)
    # Requested boundaries may themselves be holidays, outside the generated
    # calendar's first/last session. Filter sessions rather than querying a
    # session-bounded API with those non-session dates.
    sessions = calendar.sessions.tz_localize(None)
    return sessions[(sessions >= pd.Timestamp(config.start)) & (sessions <= end)].rename("Date")


def audit_prices(
    frames: dict[str, pd.DataFrame],
    config: DataConfig,
    sessions: pd.DatetimeIndex,
) -> PriceAudit:
    """Flag suspicious observations; never interpolate, repair or delete outliers."""
    if sessions.empty or not sessions.is_unique or not sessions.is_monotonic_increasing:
        raise ValueError("Trading sessions must be nonempty, unique and sorted")
    if set(frames) != set(config.tickers):
        raise ValueError("Inputs do not match configured ticker universe")
    flags, coverage, columns = [], [], {}

    def flag(date, ticker, kind, severity, value, disposition):
        flags.append(
            {
                "date": pd.Timestamp(date).date().isoformat(),
                "ticker": ticker,
                "kind": kind,
                "severity": severity,
                "value": value,
                "disposition": disposition,
            }
        )

    for ticker in config.tickers:
        frame = frames[ticker]
        if frame.empty or not {"Adj Close", "Close"}.issubset(frame):
            raise ValueError(f"{ticker}: empty data or missing adjusted/close fields")
        if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
            raise ValueError(f"{ticker}: dates must be unique and ordered; raw data retained")
        if frame.index.tz is not None or not frame.index.equals(frame.index.normalize()):
            raise ValueError(f"{ticker}: expected naive exchange-local session dates")
        adjusted = pd.to_numeric(frame["Adj Close"], errors="raise")
        close = pd.to_numeric(frame["Close"], errors="raise")
        outside = adjusted.index.difference(sessions)
        for date in outside:
            flag(
                date,
                ticker,
                "unexpected_session",
                "error",
                adjusted.loc[date],
                "Stop; inspect provider/calendar mismatch",
            )
        price = adjusted.reindex(sessions)
        valid = price.notna() & np.isfinite(price) & (price > 0)
        if not valid.any():
            raise ValueError(f"{ticker}: no valid positive adjusted prices")
        first = price.index[valid][0]
        for date in price.index[price.notna() & (~np.isfinite(price) | (price <= 0))]:
            flag(
                date,
                ticker,
                "invalid_adjusted_price",
                "error",
                price.loc[date],
                "Stop; investigate, no automatic repair",
            )
        for date in price.index[(price.index >= first) & price.isna()]:
            flag(
                date,
                ticker,
                "missing_session_price",
                "error",
                None,
                "Stop; no fill and no return bridging across missing sessions",
            )
        raw_close = close.reindex(sessions)
        for date in raw_close.index[
            (price.index >= first) & (raw_close.isna() | ~np.isfinite(raw_close) | (raw_close <= 0))
        ]:
            flag(
                date,
                ticker,
                "invalid_close",
                "error",
                raw_close.loc[date],
                "Stop; provider adjustment field cannot be checked",
            )
        returns = price.pct_change(fill_method=None)
        for date in returns.index[returns.abs() >= config.jump_threshold]:
            flag(
                date,
                ticker,
                "large_daily_return",
                "review",
                returns.loc[date],
                "Retained; team must distinguish market event from data error",
            )
        flat = returns.abs().lt(1e-12)
        run_length = flat.groupby((~flat).cumsum()).cumsum()
        for date in price.index[run_length >= config.flat_sessions]:
            flag(
                date,
                ticker,
                "flat_price_run",
                "review",
                price.loc[date],
                "Retained; inspect trading/quote activity",
            )
        factor = price / raw_close
        factor_change = factor.pct_change(fill_method=None)
        for date in factor.index[factor_change.abs() >= config.jump_threshold]:
            flag(
                date,
                ticker,
                "adjustment_factor_jump",
                "review",
                factor_change.loc[date],
                "Retained; reconcile with dividend/split fields",
            )
        # A screening heuristic, not a formal structural-break test or trading signal.
        ratio = returns.rolling(20).std() / returns.shift(20).rolling(60).std()
        for date in ratio.index[ratio >= config.volatility_ratio_threshold]:
            flag(
                date,
                ticker,
                "volatility_shift_candidate",
                "review",
                ratio.loc[date],
                "Retained; descriptive regime-change screen, not a proven break",
            )
        coverage.append(
            {
                "ticker": ticker,
                "source_rows": len(frame),
                "first_valid": first.date().isoformat(),
                "last_valid": price.index[valid][-1].date().isoformat(),
                "leading_sessions_without_data": int((sessions < first).sum()),
                "missing_sessions_after_first": int(((sessions >= first) & price.isna()).sum()),
                "valid_prices": int(valid.sum()),
            }
        )
        columns[ticker] = price
    panel = pd.DataFrame(columns, index=sessions)
    common_start = max(pd.Timestamp(row["first_valid"]) for row in coverage)
    panel = panel.loc[common_start:]
    panel.index.name = "Date"
    if len(panel) < config.minimum_prices:
        raise ValueError(f"Only {len(panel)} common prices; need {config.minimum_prices}")
    flags_frame = pd.DataFrame(
        flags, columns=["date", "ticker", "kind", "severity", "value", "disposition"]
    )
    return PriceAudit(panel, flags_frame, pd.DataFrame(coverage))


def calculate_returns(prices: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    if len(prices) < 2 or prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("Returns need at least two ordered, unique observations")
    if not np.isfinite(prices.to_numpy()).all() or (prices <= 0).any().any():
        raise ValueError("Invalid/missing prices: refusing to fill or bridge a gap")
    simple = prices.pct_change(fill_method=None).iloc[1:]
    log = np.log(prices).diff().iloc[1:]
    return simple, log


def align_risk_free(
    rates: pd.Series,
    price_dates: pd.DatetimeIndex,
    max_age_days: int,
) -> pd.DataFrame:
    """Approximate cash accrual; only observation dates strictly before period start."""
    if len(price_dates) < 2 or not price_dates.is_unique or not price_dates.is_monotonic_increasing:
        raise ValueError("Risk-free alignment needs ordered unique price dates")
    if rates.index.has_duplicates or not rates.index.is_monotonic_increasing:
        raise ValueError("Rate observations must be unique and ordered")
    valid = rates.dropna()
    if valid.empty or not np.isfinite(valid.to_numpy()).all() or (valid <= -100).any():
        raise ValueError("Invalid or missing risk-free yields")
    periods = pd.DataFrame({"period_start": price_dates[:-1], "Date": price_dates[1:]})
    quotes = pd.DataFrame({"observation_date": valid.index, "annual_yield_percent": valid.values})
    joined = pd.merge_asof(
        periods,
        quotes,
        left_on="period_start",
        right_on="observation_date",
        direction="backward",
        allow_exact_matches=False,
    )
    joined["quote_age_at_start_days"] = (joined.period_start - joined.observation_date).dt.days
    if (
        joined.observation_date.isna().any()
        or (joined.quote_age_at_start_days > max_age_days).any()
    ):
        raise ValueError("Missing/stale lagged risk-free quote; no future-rate backfill permitted")
    joined["calendar_days"] = (joined.Date - joined.period_start).dt.days
    # Investment-basis yield approximated as simple ACT/365 cash accrual.
    # It is not a directly observed holding-period Treasury total return.
    joined["simple_return"] = joined.annual_yield_percent / 100 * joined.calendar_days / 365
    if (joined.simple_return <= -1).any():
        raise ValueError("Risk-free accrual would imply non-positive wealth")
    joined["log_return"] = np.log1p(joined.simple_return)
    return joined.set_index("Date")
