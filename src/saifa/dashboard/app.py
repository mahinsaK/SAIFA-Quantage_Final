"""Streamlit application composition for the SAIFA dashboard."""

from pathlib import Path

from saifa.dashboard.startup import configure_environment, configure_page
from saifa.data.snapshots import resolve_snapshot
from saifa.domain.dashboard import DashboardDataError


def main(root: Path) -> None:
    configure_environment(root)
    configure_page()
    from saifa.dashboard.cache import bundle_path, load_verified_bundle
    from saifa.dashboard.render import render_page
    from saifa.dashboard.sidebar import render_sidebar

    try:
        snapshot = resolve_snapshot(root)
        bundle = load_verified_bundle(root, bundle_path(root, snapshot.name))
    except (DashboardDataError, ValueError, OSError) as exc:
        import streamlit as st

        st.error("Research results are not ready to display.")
        st.write(str(exc))
        st.info(
            "Prepare the app's results from the included frozen snapshot. This runs offline and "
            "can take several minutes; then reload this page."
        )
        st.code("uv run --locked python commands/run_app_data.py", language="bash")
        st.caption(
            "If the frozen snapshot is missing, restore the submission snapshot from the "
            "repository. The app does not download replacement data or display example results."
        )
        return
    selection = render_sidebar(bundle)
    render_page(bundle, selection)
