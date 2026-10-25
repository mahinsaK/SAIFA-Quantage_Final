"""Reproduce data and build the 40/60 baseline portfolio without downloading."""

import argparse
import sys
from pathlib import Path

from saifa.application.portfolio_pipeline import build_baseline_portfolio
from saifa.data.snapshots import resolve_snapshot
from saifa.domain.config import BaselinePortfolioConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="Frozen snapshot directory name; default data/LATEST")
    parser.add_argument(
        "--cost-bps", type=float, default=10.0, help="Gross traded-notional cost in basis points"
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        snapshot = resolve_snapshot(root, args.snapshot)
        config = BaselinePortfolioConfig(transaction_cost_bps=args.cost_bps)
        output = build_baseline_portfolio(root, snapshot, config)
        print(f"Baseline portfolio outputs: {output}")
        print("See docs/final/03-baseline/03-manual-accounting-check.md for human review status.")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports the failure and exits nonzero.
        print(f"Portfolio pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
