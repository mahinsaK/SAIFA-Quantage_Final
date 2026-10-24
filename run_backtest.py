"""Reproduce past-only daily VaR forecasts, coverage tests and Basel diagnostics offline."""

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parent / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(Path(__file__).resolve().parent / ".cache"))

from src.application.backtest_pipeline import build_backtest
from src.data.snapshots import resolve_snapshot
from src.domain.config import BacktestConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot")
    parser.add_argument("--start", default="2019-01-01", help="First forecast date (inclusive)")
    parser.add_argument("--end-exclusive", default="2026-10-23")
    parser.add_argument("--lookback", type=int, default=1000)
    parser.add_argument("--confidence", type=float, nargs="+", default=[0.95, 0.99])
    parser.add_argument("--simulations", type=int, default=200000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    try:
        config = BacktestConfig(
            start=args.start,
            end_exclusive=args.end_exclusive,
            lookback_observations=args.lookback,
            confidence_levels=tuple(args.confidence),
            simulations=args.simulations,
            seed=args.seed,
        )
        output = build_backtest(
            root,
            resolve_snapshot(root, args.snapshot),
            config,
            progress=lambda n, total: print(f"Forecast sessions: {n}/{total}", flush=True),
        )
        print(f"Backtest outputs: {output}")
        print("Read backtest_report.md and docs/final/manual-backtest-check.md.")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary
        print(f"Backtest failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
