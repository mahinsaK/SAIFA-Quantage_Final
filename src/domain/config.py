"""Explicit data assumptions, saved with every acquired snapshot."""

from dataclasses import dataclass
from datetime import date

UNIVERSE = ("SPY", "EFA", "EEM", "AGG", "GLD", "XLE", "XLK")


@dataclass(frozen=True)
class DataConfig:
    start: str = "2004-01-01"
    end_exclusive: str = "2026-10-23"
    tickers: tuple[str, ...] = UNIVERSE
    risk_free_series: str = "DGS3MO"
    calendar: str = "XNYS"
    jump_threshold: float = 0.10
    flat_sessions: int = 5
    volatility_ratio_threshold: float = 3.0
    max_rate_age_days: int = 7
    minimum_prices: int = 252

    def __post_init__(self) -> None:
        if date.fromisoformat(self.start) >= date.fromisoformat(self.end_exclusive):
            raise ValueError("Start must precede exclusive end date")
        if not self.tickers or len(self.tickers) != len(set(self.tickers)):
            raise ValueError("Tickers must be nonempty and unique")
        if not set(self.tickers).issubset(UNIVERSE):
            raise ValueError("Only the seven prescribed ETFs are eligible")
        if self.risk_free_series != "DGS3MO" or self.calendar != "XNYS":
            raise ValueError("This version implements DGS3MO and XNYS only")
        if not 0 < self.jump_threshold < 1 or self.flat_sessions < 2:
            raise ValueError("Invalid quality-check thresholds")
        if self.volatility_ratio_threshold <= 1 or self.max_rate_age_days < 1:
            raise ValueError("Invalid volatility or rate-age threshold")
        if self.minimum_prices < 2:
            raise ValueError("At least two prices are required")
