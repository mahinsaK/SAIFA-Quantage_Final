"""Build constrained Markowitz candidates and evaluate them against the baseline."""

import argparse
import sys
from pathlib import Path

from saifa.application.optimisation_pipeline import build_optimised_portfolios
from saifa.data.snapshots import resolve_snapshot
from saifa.domain.config import OptimisationConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", help="Frozen snapshot directory name; default data/LATEST")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    try:
        output = build_optimised_portfolios(root, resolve_snapshot(root, args.snapshot), OptimisationConfig())
        print(f"Optimisation outputs: {output}")
        print("Human review remains pending; follow docs/final/04-optimisation/03-manual-optimisation-check.md.")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports failure.
        print(f"Optimisation pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
