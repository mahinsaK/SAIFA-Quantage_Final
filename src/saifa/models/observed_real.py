"""Retrospective purchasing-power growth from costed NAV and observed monthly CPI."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class ObservedRealResult:
    strategy: str
    start_date: str
    end_date: str
    cpi_start_month: str
    cpi_end_month: str
    cpi_start: float
    cpi_end: float
    cpi_deflator: float
    initial_capital: float
    ending_nominal_wealth: float
    ending_real_wealth: float
    annualised_real_growth: float
    objective: float
    objective_met_in_observed_period: bool
    elapsed_days: int


def observed_real_growth(
    strategy: str,
    daily: pd.DataFrame,
    cpi: pd.Series,
    initial_capital: float,
    objective: float,
    as_of: str,
) -> ObservedRealResult:
    """Use the last trading session of the latest CPI month released by as-of.

    The first month's CPI is a retrospective monthly price-level approximation.
    It is not used to fit portfolio weights or issue a historical forecast.
    """
    frame = daily.copy()
    dates = pd.DatetimeIndex(frame.index)
    frame.index = dates
    if (
        len(dates) < 2
        or dates.has_duplicates
        or not dates.is_monotonic_increasing
        or dates[-1] > pd.Timestamp(as_of)
        or not np.isfinite([initial_capital, objective]).all()
        or initial_capital <= 0
        or objective <= -1
    ):
        raise ValueError("Observed real-growth inputs have invalid dates or capital")
    nav = frame.nav.to_numpy(dtype=float)
    if not np.isfinite(nav).all() or np.any(nav <= 0):
        raise ValueError("Observed real growth needs positive, finite costed NAV")
    start = dates[0]
    start_month = start.to_period("M").to_timestamp()
    end_month = cpi.index[-1]
    if start_month not in cpi.index or end_month <= start_month:
        raise ValueError("CPI does not cover the observed portfolio period")
    endpoints = np.array([cpi.loc[start_month], cpi.loc[end_month]], dtype=float)
    if not np.isfinite(endpoints).all() or np.any(endpoints <= 0):
        raise ValueError("Observed real growth needs both positive CPI endpoint values")
    matching = dates[dates.to_period("M") == end_month.to_period("M")]
    if matching.empty:
        raise ValueError("No portfolio session exists in the latest available CPI month")
    end = matching[-1]
    end_nav = float(frame.loc[end, "nav"])
    deflator = float(cpi.loc[end_month] / cpi.loc[start_month])
    real_wealth = end_nav / deflator
    days = (end - start).days
    growth = (real_wealth / initial_capital) ** (365.25 / days) - 1
    return ObservedRealResult(
        strategy=strategy,
        start_date=str(start.date()),
        end_date=str(end.date()),
        cpi_start_month=str(start_month.date()),
        cpi_end_month=str(end_month.date()),
        cpi_start=float(cpi.loc[start_month]),
        cpi_end=float(cpi.loc[end_month]),
        cpi_deflator=deflator,
        initial_capital=initial_capital,
        ending_nominal_wealth=end_nav,
        ending_real_wealth=real_wealth,
        annualised_real_growth=growth,
        objective=objective,
        objective_met_in_observed_period=bool(growth >= objective),
        elapsed_days=days,
    )
