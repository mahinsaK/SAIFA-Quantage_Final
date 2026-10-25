"""Reproduce one-day Historical, Parametric and Monte Carlo VaR/ES offline."""

import argparse
import sys
from pathlib import Path

from saifa.application.risk_pipeline import build_risk
from saifa.data.snapshots import resolve_snapshot
from saifa.domain.config import RiskConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="Frozen snapshot name; defaults to data/LATEST")
    parser.add_argument("--as-of", help="Observed close date YYYY-MM-DD; defaults to latest")
    parser.add_argument("--lookback", type=int, default=1_000, help="Return observations (>=250)")
    parser.add_argument("--confidence", type=float, nargs="+", default=[0.95, 0.99])
    parser.add_argument("--nav", type=float, default=10_000_000.0, help="Comparison NAV in USD")
    parser.add_argument("--simulations", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        config = RiskConfig(
            as_of=args.as_of,
            lookback_observations=args.lookback,
            confidence_levels=tuple(args.confidence),
            reference_nav=args.nav,
            simulations=args.simulations,
            seed=args.seed,
        )
        output = build_risk(root, resolve_snapshot(root, args.snapshot), config)
        print(f"Risk comparison outputs: {output}")
        print("Read risk_report.md and complete docs/final/05-risk-models/03-manual-risk-check.md.")
        return 0
    except Exception as exc:  # noqa: BLE001 - command-line boundary.
        print(f"Risk pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
