"""SAIFA: an offline, interactive investment-research dashboard."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

import pandas as pd
import streamlit as st

from src.dashboard.data import load_bundle, verify_bundle
from src.dashboard.views import (
    assumptions_page,
    backtest_page,
    portfolio_page,
    risk_page,
    stress_page,
)
from src.data.snapshots import resolve_snapshot
from src.domain.dashboard import CONFIDENCES, METHODS, STRATEGIES, DashboardDataError


@st.cache_data(show_spinner=False, max_entries=3)
def cached_bundle(root: str, path: str, verified_digest: str):
    # Digest is an explicit cache input, verified against the actual files before every call.
    return load_bundle(Path(root), Path(path))


def main(root: Path = ROOT):
    st.set_page_config(page_title="SAIFA · Endowment research", page_icon="◈", layout="wide")
    st.title("SAIFA")
    st.caption("QUANT EDGE 1.0 · SERENDIB UNIVERSITY ENDOWMENT FUND")
    st.write("**Preserve capital. Understand the risk. Make a defensible decision.**")
    try:
        snapshot = resolve_snapshot(root)
        path = root / "output/app" / snapshot.name / "bundle.json"
        digest = verify_bundle(root, path)
        with st.spinner("Loading verified research results…"):
            bundle = cached_bundle(str(root), str(path), digest)
    except (DashboardDataError, ValueError, OSError) as exc:
        st.error("Research results are not ready to display.")
        st.write(str(exc))
        st.info(
            "Prepare the app's results from the included frozen snapshot. This runs offline and can take several minutes; then reload this page."
        )
        st.code("uv run --locked python run_app_data.py", language="bash")
        st.caption(
            "If the frozen snapshot is missing, restore the submission snapshot from the repository. The app does not download replacement data or display example results."
        )
        return
    meta = bundle.metadata["backtest"]
    with st.sidebar:
        st.header("Research explorer")
        page = st.radio(
            "Page",
            ["Portfolio", "Risk comparison", "Backtesting", "Stress analysis", "Assumptions"],
            key="page",
        )
        strategy = st.selectbox(
            "Portfolio", list(STRATEGIES), format_func=STRATEGIES.get, key="strategy"
        )
        confidence = st.selectbox(
            "Confidence",
            list(CONFIDENCES),
            index=2,
            format_func=lambda c: f"{c:.0%}",
            key="confidence",
        )
        method = st.selectbox("VaR method", list(METHODS), format_func=METHODS.get, key="method")
        st.caption(
            "Confidence and method apply to risk, backtesting and available risk contributions. Scenario losses do not have an assigned confidence level."
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
        st.caption(
            "Date range changes backtesting only. Portfolio performance and crisis windows retain their stated periods."
        )
        st.divider()
        st.caption(
            f"Snapshot: {bundle.manifest['snapshot_id']}\n\nRisk as-of: {bundle.metadata['risk']['as_of']}\n\nProposed allocations · final decision pending"
        )
    if page == "Portfolio":
        portfolio_page(bundle, strategy)
    elif page == "Risk comparison":
        risk_page(bundle, strategy, confidence, method)
    elif page == "Backtesting":
        if len(dates) != 2:
            st.info("Select both a start and an end date for the backtest.")
        else:
            backtest_page(bundle, strategy, confidence, method, dates[0], dates[1])
    elif page == "Stress analysis":
        stress_page(bundle, strategy, confidence, method)
    else:
        assumptions_page(bundle)


if __name__ == "__main__":
    main()
