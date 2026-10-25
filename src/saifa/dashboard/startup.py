"""Dashboard process and Streamlit startup configuration."""

import os
from pathlib import Path

import streamlit as st


def configure_environment(root: Path) -> None:
    os.environ.setdefault("MPLCONFIGDIR", str(root / ".cache/matplotlib"))
    os.environ.setdefault("XDG_CACHE_HOME", str(root / ".cache"))


def configure_page() -> None:
    st.set_page_config(page_title="SAIFA · Endowment research", page_icon="◈", layout="wide")
    st.title("SAIFA")
    st.caption("QUANT EDGE 1.0 · SERENDIB UNIVERSITY ENDOWMENT FUND")
    st.write("**Preserve capital. Understand the risk. Make a defensible decision.**")
