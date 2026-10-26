"""Shared visual conventions for verified dashboard results."""

import pandas as pd

PORTFOLIO_COLORS = {
    "baseline_40_60": "#375A7F",
    "minimum_volatility": "#137C73",
    "maximum_sharpe": "#A46A2D",
}
RISK_COLOR = "#137C73"
LOSS_COLOR = "#B14F43"


def money(value: float) -> str:
    return "Unavailable" if pd.isna(value) else f"${value:,.2f}"


def percent(value: float) -> str:
    return "Unavailable" if pd.isna(value) else f"{value:.2%}"
