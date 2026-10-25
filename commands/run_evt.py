"""Reproduce EVT threshold diagnostics, tail estimates and uncertainty offline."""

import argparse
import os
import sys
from pathlib import Path

# Keep Matplotlib's writable font/config cache inside the ignored workspace cache.
ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

from saifa.application.evt_pipeline import build_evt
from saifa.data.snapshots import resolve_snapshot
from saifa.domain.config import EVTConfig, RiskConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot")
    parser.add_argument("--as-of")
    parser.add_argument("--lookback", type=int, default=1000)
    parser.add_argument("--confidence", type=float, nargs="+", default=[0.95, 0.99])
    parser.add_argument("--threshold", type=float, default=0.90)
    parser.add_argument("--bootstrap", type=int, default=200)
    parser.add_argument("--block-length", type=int, default=10)
    parser.add_argument("--seed", type=int, default=314159)
    args = parser.parse_args()
    root = ROOT
    try:
        risk = RiskConfig(
            as_of=args.as_of,
            lookback_observations=args.lookback,
            confidence_levels=tuple(args.confidence),
        )
        grid = tuple(sorted(set(EVTConfig().sensitivity_quantiles + (args.threshold,))))
        evt = EVTConfig(
            threshold_quantile=args.threshold,
            sensitivity_quantiles=grid,
            bootstrap_replicates=args.bootstrap,
            block_length=args.block_length,
            seed=args.seed,
        )
        output = build_evt(root, resolve_snapshot(root, args.snapshot), risk, evt)
        print(f"EVT outputs: {output}")
        print(
            "Read evt_report.md and docs/final/06-evt/03-manual-evt-check.md; review threshold diagnostics."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"EVT pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
