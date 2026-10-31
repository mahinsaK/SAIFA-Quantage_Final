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
    low, high = pd.Timestamp(meta["start"]).date(), pd.Timestamp(meta["end"]).date()
    evaluation_start = max(low, pd.Timestamp(meta["validation_end_exclusive"]).date())
    with st.sidebar:
        st.header("SAIFA research")
        page = st.radio(
            "Explore",
            [
                "Portfolio",
                "Risk comparison",
                "Backtesting",
                "Stress analysis",
                "Research lab",
                "Assumptions",
            ],
            key="page",
        )
        st.divider()
        if page == "Research lab":
            st.caption(
                "Choose a research question and adjust its controls in the main area. "
                "Your selections on the original pages are remembered."
            )
            st.caption(
                f"Snapshot: {bundle.manifest['snapshot_id']}\n\n"
                "Retrospective research · human validation pending"
            )
            return DashboardSelection(
                page,
                st.session_state.get("strategy", next(iter(STRATEGIES))),
                st.session_state.get("confidence", CONFIDENCES[-1]),
                st.session_state.get("method", next(iter(METHODS))),
                tuple(st.session_state.get("dates", (evaluation_start, high))),
            )
        strategy = st.selectbox(
            "Portfolio",
            list(STRATEGIES),
            format_func=STRATEGIES.get,
            key="strategy",
            persist_state="session",
        )
        st.caption("Portfolio selection changes the detailed evidence, not the committee decision.")
        st.subheader("Risk settings")
        confidence = st.selectbox(
            "Confidence",
            list(CONFIDENCES),
            index=2,
            format_func=lambda value: f"{value:.0%}",
            key="confidence",
            persist_state="session",
        )
        method = st.selectbox(
            "VaR method",
            list(METHODS),
            format_func=METHODS.get,
            key="method",
            persist_state="session",
        )
        st.caption(
            "Confidence and method apply to risk and backtesting. Crisis and hypothetical shocks "
            "have no confidence level."
        )
        if "dates" not in st.session_state:
            st.session_state["dates"] = (evaluation_start, high)
        dates = st.date_input(
            "Backtest date range (inclusive)",
            min_value=low,
            max_value=high,
            format="YYYY-MM-DD",
            key="dates",
            persist_state="session",
        )
        st.caption(
            "Dates change backtesting only. Use the period buttons at the top of Backtesting for a quick choice, or set a custom range here."
        )
        st.divider()
        st.caption(
            f"Snapshot: {bundle.manifest['snapshot_id']}\n\n"
            f"Risk as-of: {bundle.metadata['risk']['as_of']}\n\n"
            "Proposed allocations · final decision pending"
        )
    return DashboardSelection(page, strategy, confidence, method, tuple(dates))
