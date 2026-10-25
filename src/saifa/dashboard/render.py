"""Dashboard page dispatch."""

import streamlit as st

from saifa.dashboard.sidebar import DashboardSelection
from saifa.dashboard.views import (
    assumptions_page,
    backtest_page,
    portfolio_page,
    risk_page,
    stress_page,
)
from saifa.domain.dashboard import DashboardBundle


def render_page(bundle: DashboardBundle, selection: DashboardSelection) -> None:
    if selection.page == "Portfolio":
        portfolio_page(bundle, selection.strategy)
    elif selection.page == "Risk comparison":
        risk_page(bundle, selection.strategy, selection.confidence, selection.method)
    elif selection.page == "Backtesting":
        if len(selection.dates) != 2:
            st.info("Select both a start and an end date for the backtest.")
        else:
            backtest_page(
                bundle,
                selection.strategy,
                selection.confidence,
                selection.method,
                selection.dates[0],
                selection.dates[1],
            )
    elif selection.page == "Stress analysis":
        stress_page(bundle, selection.strategy, selection.confidence, selection.method)
    else:
        assumptions_page(bundle)
