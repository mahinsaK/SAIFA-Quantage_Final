"""Build the annual portfolio experiment from the existing verified offline bundle."""

import sys
from pathlib import Path

from saifa.application.adaptive_pipeline import build_adaptive
from saifa.data.snapshots import resolve_snapshot


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    try:
        print(f"Annual strategy evidence: {build_adaptive(root, resolve_snapshot(root))}")
        print(
            "Retrospective experiment only. Human review and adaptive risk validation remain pending."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports the failure without substitution.
        print(f"Annual strategy failed: {exc}", file=sys.stderr)
        print("First prepare the frozen app bundle with commands/run_app_data.py", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
