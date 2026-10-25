"""Verified dashboard bundle loading and Streamlit caching."""

from pathlib import Path

import streamlit as st

from saifa.dashboard.data import load_bundle, verify_bundle
from saifa.domain.dashboard import DashboardBundle


def bundle_path(root: Path, snapshot_name: str) -> Path:
    return root / "output/app" / snapshot_name / "bundle.json"


def load_verified_bundle(root: Path, path: Path) -> DashboardBundle:
    digest = verify_bundle(root, path)
    return cached_bundle(str(root), str(path), digest)


@st.cache_data(show_spinner=False, max_entries=3)
def cached_bundle(root: str, path: str, verified_digest: str) -> DashboardBundle:
    """Cache only after the caller verifies the current manifest and outputs."""
    return load_bundle(Path(root), Path(path))
