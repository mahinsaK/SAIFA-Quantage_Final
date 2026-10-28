"""Dashboard page dispatch."""

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
        backtest_page(
            bundle,
            selection.strategy,
            selection.confidence,
            selection.method,
            selection.dates,
        )
    elif selection.page == "Stress analysis":
        stress_page(bundle, selection.strategy, selection.confidence, selection.method)
    else:
        assumptions_page(bundle)
