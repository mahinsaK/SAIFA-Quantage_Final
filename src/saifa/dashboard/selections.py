"""Pure selection logic; financial formulas are delegated to the tested model layer."""

from dataclasses import asdict

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from saifa.domain.config import UNIVERSE, BacktestConfig
from saifa.domain.dashboard import METHODS, STRATEGIES, BacktestView, DashboardDataError
from saifa.models.backtesting import basel_traffic_light, christoffersen_test, kupiec_test


def frontier_display_data(
    frontier: pd.DataFrame, candidates: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Prepare development-only frontier coordinates without refitting the optimiser."""
    curve_fields = ("volatility", "expected_return")
    point_fields = (
        "strategy",
        "development_volatility",
        "development_expected_return",
        "solver_success",
    )
    if not set(curve_fields).issubset(frontier) or not set(point_fields).issubset(candidates):
        raise DashboardDataError("Development frontier or candidate estimates are missing")
    names = ("minimum_volatility", "maximum_sharpe")
    if candidates.strategy.duplicated().any() or set(candidates.strategy) != set(names):
        raise DashboardDataError("Development candidate estimates are incomplete")
    if not candidates.solver_success.eq(True).all():
        raise DashboardDataError("A development candidate did not converge")
    curve = frontier.loc[:, list(curve_fields)].apply(pd.to_numeric, errors="coerce")
    points = (
        candidates.set_index("strategy")
        .loc[list(names), list(point_fields[1:3])]
        .apply(pd.to_numeric, errors="coerce")
    )
    if (
        curve.empty
        or not np.isfinite(curve.to_numpy()).all()
        or not np.isfinite(points.to_numpy()).all()
        or (curve.volatility <= 0).any()
        or (points.development_volatility <= 0).any()
    ):
        raise DashboardDataError("Development frontier has unavailable or invalid estimates")
    curve = curve.rename(
        columns={
            "volatility": "Annual volatility (%)",
            "expected_return": "Expected annual return (%)",
        }
    ).mul(100)
    points = points.rename(
        columns={
            "development_volatility": "Annual volatility (%)",
            "development_expected_return": "Expected annual return (%)",
        }
    ).mul(100)
    points.insert(0, "Portfolio", [STRATEGIES[name] for name in names])
    return curve.sort_values("Annual volatility (%)"), points.reset_index(drop=True)


def recent_return_correlations(
    returns: pd.DataFrame, sessions: int = 252
) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp]:
    """Describe the latest aligned ETF returns; do not refit portfolio weights."""
    if sessions < 2 or not {"Date", *UNIVERSE}.issubset(returns):
        raise DashboardDataError("ETF return dates or columns are unavailable")
    if len(returns) < sessions:
        raise DashboardDataError(f"Fewer than {sessions} aligned ETF returns are available")
    dates = pd.to_datetime(returns.Date, errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise DashboardDataError("ETF return dates are invalid or out of order")
    recent = returns.loc[:, list(UNIVERSE)].tail(sessions).apply(pd.to_numeric, errors="coerce")
    if not np.isfinite(recent.to_numpy()).all():
        raise DashboardDataError("Latest ETF returns contain missing or invalid values")
    correlations = recent.corr(method="pearson")
    if not np.isfinite(correlations.to_numpy()).all():
        raise DashboardDataError("ETF correlation is unavailable for a constant return series")
    return correlations, dates.iloc[-sessions], dates.iloc[-1]


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


def backtest_comparison(
    forecasts: pd.DataFrame,
    confidence: float,
    start,
    end,
    config: BacktestConfig,
    validation_end_exclusive: str,
    periods: tuple[str, ...],
) -> pd.DataFrame:
    """Recalculate every model from the same dated forecasts and selected range."""
    rows = []
    for strategy in STRATEGIES:
        for method in METHODS:
            try:
                tests = backtest_view(
                    forecasts,
                    strategy,
                    method,
                    confidence,
                    start,
                    end,
                    config,
                    validation_end_exclusive,
                ).tests.set_index("period")
            except DashboardDataError as exc:
                tests = pd.DataFrame()
                reason = str(exc)
            else:
                reason = ""
            for period in periods:
                test = tests.loc[period] if period in tests.index else None
                for check, prefix in (("Kupiec", "coverage"), ("Christoffersen", "independence")):
                    if test is None:
                        reason_text = reason or "No forecast summary for this period"
                    else:
                        warning = test[f"{prefix}_warning"]
                        reason_text = "" if pd.isna(warning) else str(warning)
                    rows.append(
                        {
                            "Period": period,
                            "Portfolio": STRATEGIES[strategy],
                            "Method": METHODS[method],
                            "Check": check,
                            "Decision": (
                                str(test[f"{prefix}_decision"])
                                if test is not None
                                else "unavailable"
                            ),
                            "p-value": (test[f"{prefix}_p_value"] if test is not None else np.nan),
                            "Sessions": (test.coverage_observations if test is not None else 0),
                            "Exceptions": (
                                test.coverage_exceptions if test is not None else np.nan
                            ),
                            "Missing forecasts": (
                                test.coverage_missing_forecasts if test is not None else np.nan
                            ),
                            "Reason": reason_text,
                        }
                    )
    return pd.DataFrame(rows)
