"""Acquire explicitly; otherwise reproduce a frozen snapshot without network calls."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from saifa.application.data_pipeline import build_data
from saifa.data.providers import FredRates, YahooPrices
from saifa.data.snapshots import acquire, resolve_snapshot
from saifa.domain.config import DataConfig


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--download", action="store_true", help="Acquire a new immutable snapshot")
    group.add_argument("--snapshot", help="Rebuild a specific snapshot directory name")
    parser.add_argument("--start", help="Download start inclusive (default 2004-01-01)")
    parser.add_argument("--end", help="Download end exclusive (default today's New York date)")
    args = parser.parse_args()
    if (args.start or args.end) and not args.download:
        parser.error("--start/--end only apply to --download; frozen config is used otherwise")
    root = Path(__file__).resolve().parents[1]
    try:
        if args.download:
            today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
            config = DataConfig(start=args.start or "2004-01-01", end_exclusive=args.end or today)
            if config.end_exclusive > today:
                raise ValueError("End must exclude today's incomplete New York session")
            snapshot = acquire(root, config, YahooPrices(root / ".cache/yfinance"), FredRates())
        else:
            snapshot = resolve_snapshot(root, args.snapshot)
        output = build_data(root, snapshot)
        print(f"Data products: {output}")
        print("Read quality_report.md and quality_flags.csv before using the data.")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports provider failures and exits nonzero.
        print(f"Data pipeline failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
