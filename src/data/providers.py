"""External sources. No portfolio transformations belong here."""

from io import StringIO
from pathlib import Path
from typing import Protocol

import pandas as pd
import requests
import yfinance as yf


class PriceProvider(Protocol):
    def fetch(self, ticker: str, start: str, end: str) -> pd.DataFrame: ...


class RateProvider(Protocol):
    def fetch_csv(self, series: str, start: str, end: str) -> str: ...


class YahooPrices:
    def __init__(self, cache: Path):
        cache.mkdir(parents=True, exist_ok=True)
        yf.set_tz_cache_location(str(cache))

    def fetch(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        frame = yf.Ticker(ticker).history(
            start=start,
            end=end,
            interval="1d",
            auto_adjust=False,
            back_adjust=False,
            actions=True,
            repair=False,
            keepna=True,
            rounding=False,
            timeout=30,
            raise_errors=True,
        )
        if frame.empty or not {"Close", "Adj Close"}.issubset(frame.columns):
            raise ValueError(f"{ticker}: missing prices or explicit Adj Close field")
        # Preserve the exchange-local session date, not a UTC-shifted calendar date.
        frame.index = pd.DatetimeIndex(frame.index).tz_localize(None).normalize()
        frame.index.name = "Date"
        return frame


class FredRates:
    def fetch_csv(self, series: str, start: str, end: str) -> str:
        response = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv",
            params={"id": series, "cosd": start, "coed": end},
            timeout=45,
        )
        response.raise_for_status()
        parse_fred(response.text, series)  # Validate schema before accepting a snapshot.
        return response.text


def parse_fred(text: str, series: str) -> pd.Series:
    frame = pd.read_csv(StringIO(text), na_values=["."])
    if series not in frame or frame.empty:
        raise ValueError(f"FRED response lacks {series} observations")
    dates = pd.to_datetime(frame.iloc[:, 0], errors="raise")
    values = pd.to_numeric(frame[series], errors="raise")
    result = pd.Series(values.to_numpy(), index=pd.DatetimeIndex(dates), name=series)
    if result.index.has_duplicates or not result.index.is_monotonic_increasing:
        raise ValueError("FRED dates must be unique and ordered")
    if result.notna().sum() == 0:
        raise ValueError("FRED returned no numeric observations")
    result.index.name = "Date"
    return result
