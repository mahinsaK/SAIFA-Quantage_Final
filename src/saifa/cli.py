"""Installed command-line entry points for SAIFA pipelines."""

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from saifa.application.dashboard_pipeline import build_dashboard
from saifa.application.data_pipeline import build_data
from saifa.application.risk_pipeline import build_risk
from saifa.data.providers import FredRates, YahooPrices
from saifa.data.snapshots import acquire, resolve_snapshot
from saifa.domain.config import DataConfig, RiskConfig


def _root() -> Path:
    return Path.cwd()


def data_main() -> int:
    parser = argparse.ArgumentParser(description="Acquire or rebuild a frozen data snapshot.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--download", action="store_true")
    group.add_argument("--snapshot")
    parser.add_argument("--start")
    parser.add_argument("--end")
    args = parser.parse_args()
    if (args.start or args.end) and not args.download:
        parser.error("--start/--end only apply to --download")
    root = _root()
    try:
        if args.download:
            today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
            config = DataConfig(
                start=args.start or "2004-01-01",
                end_exclusive=args.end or today,
            )
            if config.end_exclusive > today:
                raise ValueError("End must exclude today's incomplete New York session")
            snapshot = acquire(root, config, YahooPrices(root / ".cache/yfinance"), FredRates())
        else:
            snapshot = resolve_snapshot(root, args.snapshot)
        print(f"Data products: {build_data(root, snapshot)}")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports failures and exits nonzero.
        print(f"Data pipeline failed: {exc}", file=sys.stderr)
        return 1


def risk_main() -> int:
    parser = argparse.ArgumentParser(description="Reproduce risk comparison outputs.")
    parser.add_argument("--snapshot")
    parser.add_argument("--as-of")
    parser.add_argument("--lookback", type=int, default=1_000)
    parser.add_argument("--confidence", type=float, nargs="+", default=[0.95, 0.99])
    parser.add_argument("--nav", type=float, default=10_000_000.0)
    parser.add_argument("--simulations", type=int, default=200_000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    root = _root()
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
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports failures and exits nonzero.
        print(f"Risk pipeline failed: {exc}", file=sys.stderr)
        return 1


def dashboard_data_main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the Streamlit dashboard data bundle.")
    parser.add_argument("--snapshot")
    args = parser.parse_args()
    root = _root()
    try:
        output = build_dashboard(
            root,
            resolve_snapshot(root, args.snapshot),
            progress=lambda message: print(message, flush=True),
        )
        print(f"App bundle: {output}")
        return 0
    except Exception as exc:  # noqa: BLE001 - CLI boundary reports failures and exits nonzero.
        print(f"App preparation failed: {exc}", file=sys.stderr)
        return 1
