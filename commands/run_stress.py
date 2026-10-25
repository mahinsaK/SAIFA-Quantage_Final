"""Reproduce risk contributions and historical/hypothetical stress analysis offline."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

from saifa.application.stress_pipeline import build_stress
from saifa.data.snapshots import resolve_snapshot
from saifa.domain.config import RiskConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot")
    parser.add_argument("--as-of")
    parser.add_argument("--lookback", type=int, default=1000)
    parser.add_argument("--confidence", type=float, nargs="+", default=[0.95, 0.99])
    args = parser.parse_args()
    root = ROOT
    try:
        risk = RiskConfig(
            as_of=args.as_of,
            lookback_observations=args.lookback,
            confidence_levels=tuple(args.confidence),
        )
        output = build_stress(root, resolve_snapshot(root, args.snapshot), risk)
        print(f"Stress outputs: {output}")
        print(
            "Read stress_report.md and docs/final/08-contributions-stress/03-manual-stress-check.md."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"Stress analysis failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
