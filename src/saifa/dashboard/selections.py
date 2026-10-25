"""Pure selection logic; financial formulas are delegated to the tested model layer."""

from dataclasses import asdict

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from saifa.domain.config import BacktestConfig
from saifa.domain.dashboard import METHODS, BacktestView, DashboardDataError
from saifa.models.backtesting import basel_traffic_light, christoffersen_test, kupiec_test


def select_risk(comparison: pd.DataFrame, strategy: str, confidence: float) -> pd.DataFrame:
    selected = comparison.loc[
        (comparison.strategy == strategy) & (comparison.confidence == confidence)
    ]
    if selected.empty or selected.method.duplicated().any():
        raise DashboardDataError(
            "No unique risk comparison for the selected portfolio and confidence"
        )
    return selected.set_index("method").reindex(list(METHODS)).reset_index()


def backtest_view(
    forecasts: pd.DataFrame,
    strategy: str,
    method: str,
    confidence: float,
    start,
    end,
    config: BacktestConfig,
    validation_end_exclusive: str,
) -> BacktestView:
    """Inclusive user dates; preserve missing sessions and split at the original period boundary."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start > end:
        raise DashboardDataError("Backtest start date must be on or before the end date")
    if start < pd.Timestamp(config.start) or end >= pd.Timestamp(config.end_exclusive):
        raise DashboardDataError("Selected dates fall outside the prepared forecast range")
    calendar = xcals.get_calendar(
        "XNYS", start=start - pd.Timedelta(days=7), end=end + pd.Timedelta(days=7)
    )
    sessions = calendar.sessions.tz_localize(None)
    sessions = sessions[(sessions >= start) & (sessions <= end)]
    if sessions.empty:
        raise DashboardDataError("The selected range contains no exchange sessions")
    chosen = forecasts.loc[
        (forecasts.strategy == strategy)
        & (forecasts.method == method)
        & (forecasts.confidence == confidence)
    ].copy()
    if chosen.empty:
        raise DashboardDataError("No forecasts were prepared for this selection")
    chosen["forecast_date"] = pd.to_datetime(chosen.forecast_date)
    if chosen.forecast_date.duplicated().any():
        raise DashboardDataError("Duplicate forecast date")
    chosen = chosen.set_index("forecast_date").reindex(sessions)
    chosen.index.name = "forecast_date"
    chosen["period"] = np.where(
        chosen.index < pd.Timestamp(validation_end_exclusive), "validation", "evaluation"
    )
    available = np.isfinite(chosen.var_fraction) & np.isfinite(chosen.loss_fraction)
    chosen["exception"] = np.where(
        available, (chosen.loss_fraction > chosen.var_fraction).astype(float), np.nan
    )
    chosen["warning"] = chosen.warning.fillna("No forecast available for this session")
    chosen["status"] = chosen.status.fillna("missing")
    chosen = chosen.reset_index()
    summaries, lights = [], []
    for period, group in chosen.groupby("period", sort=False):
        hits = group.exception.to_numpy(dtype=float)
        coverage = kupiec_test(hits, confidence, config.significance)
        independence = christoffersen_test(hits, config.significance, config.minimum_previous_state)
        identity = {
            "period": period,
            "start": group.forecast_date.iloc[0],
            "end": group.forecast_date.iloc[-1],
        }
        summaries.append(
            dict(
                **identity,
                **{f"coverage_{k}": v for k, v in asdict(coverage).items()},
                **{f"independence_{k}": v for k, v in asdict(independence).items()},
            )
        )
        tail = group.tail(250)
        lights.append(
            dict(
                period=period,
                start=tail.forecast_date.iloc[0],
                end=tail.forecast_date.iloc[-1],
                **asdict(basel_traffic_light(tail.exception, confidence)),
            )
        )
    return BacktestView(chosen, pd.DataFrame(summaries), pd.DataFrame(lights))
