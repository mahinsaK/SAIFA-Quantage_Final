"""Prepare the research lab offline after the frozen app bundle exists."""

import sys
from pathlib import Path

from saifa.application.research_pipeline import build_research
from saifa.data.snapshots import resolve_snapshot


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        print(
            f"Research lab: {build_research(root, resolve_snapshot(root), progress=lambda s: print(s, flush=True))}"
        )
        print("Research only. Human review, model selection and client approval remain separate.")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports failure and never substitutes results.
        print(f"Research lab failed: {exc}", file=sys.stderr)
        print("First prepare the frozen bundle: commands/run_app_data.py", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
