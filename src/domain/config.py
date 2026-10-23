"""Explicit data assumptions, saved with every acquired snapshot."""

from dataclasses import dataclass
from datetime import date
from math import isclose

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


@dataclass(frozen=True)
class BaselinePortfolioConfig:
    """Transparent comparator assumptions, not an optimised recommendation."""

    initial_capital: float = 10_000_000.0
    target_weights: tuple[tuple[str, float], ...] = (("SPY", 0.40), ("AGG", 0.60))
    transaction_cost_bps: float = 10.0
    annual_trading_days: int = 252

    def __post_init__(self) -> None:
        tickers = [ticker for ticker, _ in self.target_weights]
        weights = [weight for _, weight in self.target_weights]
        if self.initial_capital <= 0:
            raise ValueError("Initial capital must be positive")
        if not tickers or len(tickers) != len(set(tickers)):
            raise ValueError("Target tickers must be nonempty and unique")
        if not set(tickers).issubset(UNIVERSE):
            raise ValueError("Portfolio contains an ineligible ETF")
        if any(weight < 0 for weight in weights) or not isclose(sum(weights), 1.0):
            raise ValueError("Long-only target weights must sum to one")
        if not 0 <= self.transaction_cost_bps < 10_000:
            raise ValueError("Transaction cost must be between 0 and 10,000 bps")
        if self.annual_trading_days < 1:
            raise ValueError("Annual trading days must be positive")

    @property
    def tickers(self) -> tuple[str, ...]:
        return tuple(ticker for ticker, _ in self.target_weights)

    @property
    def weights(self) -> tuple[float, ...]:
        return tuple(weight for _, weight in self.target_weights)

    @property
    def transaction_cost_rate(self) -> float:
        return self.transaction_cost_bps / 10_000
