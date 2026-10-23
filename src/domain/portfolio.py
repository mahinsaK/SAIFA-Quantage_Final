"""Typed results for portfolio accounting."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class PortfolioRun:
    strategy: str
    daily: pd.DataFrame
    transactions: pd.DataFrame


@dataclass(frozen=True)
class RebalanceResult:
    values: tuple[float, ...]
    trades: tuple[float, ...]
    gross_traded: float
    cost: float
    nav_before: float
    nav_after: float
