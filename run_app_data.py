"""Prepare the Streamlit app's verified local data bundle without downloading market data."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

from src.application.dashboard_pipeline import build_dashboard
from src.data.snapshots import resolve_snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot", help="Defaults to the frozen snapshot identified by data/LATEST"
    )
    args = parser.parse_args()
    try:
        output = build_dashboard(
            ROOT,
            resolve_snapshot(ROOT, args.snapshot),
            progress=lambda message: print(message, flush=True),
        )
        print(f"App bundle: {output}")
        print("Launch: uv run --locked streamlit run app.py")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI error boundary
        print(f"App preparation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
