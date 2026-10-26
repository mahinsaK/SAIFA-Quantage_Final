"""Build committee evidence and PDFs offline from the verified Streamlit bundle."""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))

from saifa.application.decision_pipeline import build_decision
from saifa.data.snapshots import resolve_snapshot
from saifa.reporting.submission import write_submission


def main() -> int:
    try:
        snapshot = resolve_snapshot(ROOT)
        evidence = build_decision(ROOT, snapshot)
        print(f"Decision evidence: {evidence}")
        output = write_submission(ROOT, snapshot)
        print(f"Report, tear sheet and committee memo: {output}")
        print("Human recommendation, spending assumptions and scenario approval remain pending.")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"Submission preparation failed: {exc}", file=sys.stderr)
        print("First prepare: uv run --locked python commands/run_app_data.py", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
