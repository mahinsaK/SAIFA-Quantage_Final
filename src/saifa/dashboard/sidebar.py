"""Streamlit sidebar controls and their typed state."""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from saifa.domain.dashboard import CONFIDENCES, METHODS, STRATEGIES, DashboardBundle


@dataclass(frozen=True)
class DashboardSelection:
    page: str
    strategy: str
    confidence: float
    method: str
    dates: tuple[date, ...]


def render_sidebar(bundle: DashboardBundle) -> DashboardSelection:
    meta = bundle.metadata["backtest"]
    with st.sidebar:
        st.header("SAIFA research")
        page = st.radio(
            "Explore",
            ["Portfolio", "Risk comparison", "Backtesting", "Stress analysis", "Assumptions"],
            key="page",
        )
        st.divider()
        strategy = st.selectbox(
            "Portfolio", list(STRATEGIES), format_func=STRATEGIES.get, key="strategy"
        )
        st.caption("Portfolio selection changes the detailed evidence, not the committee decision.")
        st.subheader("Risk settings")
        confidence = st.selectbox(
            "Confidence",
            list(CONFIDENCES),
            index=2,
            format_func=lambda value: f"{value:.0%}",
            key="confidence",
        )
        method = st.selectbox("VaR method", list(METHODS), format_func=METHODS.get, key="method")
        st.caption(
            "Confidence and method apply to risk and backtesting. Crisis and hypothetical shocks "
            "have no confidence level."
        )
        low, high = pd.Timestamp(meta["start"]).date(), pd.Timestamp(meta["end"]).date()
        evaluation_start = max(low, pd.Timestamp(meta["validation_end_exclusive"]).date())
        dates = st.date_input(
            "Backtest date range (inclusive)",
            value=(evaluation_start, high),
            min_value=low,
            max_value=high,
            format="YYYY-MM-DD",
            key="dates",
        )
        st.caption("Dates change backtesting only.")
        st.divider()
        st.caption(
            f"Snapshot: {bundle.manifest['snapshot_id']}\n\n"
            f"Risk as-of: {bundle.metadata['risk']['as_of']}\n\n"
            "Proposed allocations · final decision pending"
        )
    return DashboardSelection(page, strategy, confidence, method, tuple(dates))
