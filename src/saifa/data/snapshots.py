"""Immutable raw snapshots with provenance and corruption detection."""

import json
import platform
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from uuid import uuid4

import pandas as pd

from saifa.data.providers import PriceProvider, RateProvider, parse_fred
from saifa.domain.config import DataConfig


def file_hash(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, content: dict) -> None:
    path.write_text(json.dumps(content, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def write_output_manifest(output: Path, snapshot_id: str, run_id: str | None = None) -> None:
    """Record every generated file without making the manifest hash itself recursive."""
    status_path = output / "status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    files = {
        str(path.relative_to(output)): file_hash(path)
        for path in sorted(output.rglob("*"))
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "schema_version": 1,
        "status": status.get("status", "unknown"),
        "snapshot_id": snapshot_id,
        "files": files,
    }
    if run_id is not None:
        manifest["run_id"] = run_id
    write_json(output / "manifest.json", manifest)


def acquire(
    root: Path,
    config: DataConfig,
    prices: PriceProvider,
    rates: RateProvider,
) -> Path:
    timestamp = datetime.now(UTC)
    identifier = timestamp.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8]
    folder = root / "data" / "snapshots" / identifier
    folder.mkdir(parents=True, exist_ok=False)
    manifest = {
        "schema_version": 1,
        "status": "incomplete",
        "snapshot_id": identifier,
        "retrieved_at_utc": timestamp.isoformat(),
        "config": asdict(config),
        "python": platform.python_version(),
        "packages": {
            p: version(p)
            for p in (
                "yfinance",
                "pandas",
                "numpy",
                "requests",
                "exchange-calendars",
                "statsmodels",
            )
        },
        "sources": {
            "prices": "Yahoo Finance via yfinance.Ticker.history",
            "risk_free": "https://fred.stlouisfed.org/series/DGS3MO",
        },
        "yahoo_settings": {
            "interval": "1d",
            "auto_adjust": False,
            "back_adjust": False,
            "actions": True,
            "repair": False,
            "keepna": True,
            "rounding": False,
        },
        "limitations": [
            "Yahoo frames are provider/library-normalised responses, not raw HTTP payloads.",
            "Adjusted prices and FRED history can be revised; this is not a point-in-time archive.",
            "Download start/end are research coverage, not train/test split dates.",
        ],
        "files": {},
    }
    write_json(folder / "manifest.json", manifest)
    try:
        for ticker in config.tickers:
            print(f"Downloading {ticker}...", flush=True)
            frame = prices.fetch(ticker, config.start, config.end_exclusive)
            if frame.empty or not {"Close", "Adj Close"}.issubset(frame.columns):
                raise ValueError(f"{ticker}: provider did not return required price fields")
            path = folder / f"{ticker}.csv"
            frame.to_csv(path, index_label="Date", float_format="%.17g")
            manifest["files"][path.name] = file_hash(path)
        start = (pd.Timestamp(config.start) - timedelta(days=14)).date().isoformat()
        end = (pd.Timestamp(config.end_exclusive) - timedelta(days=1)).date().isoformat()
        text = rates.fetch_csv(config.risk_free_series, start, end)
        parse_fred(text, config.risk_free_series)
        path = folder / "fred.csv"
        path.write_text(text, encoding="utf-8")
        manifest["files"][path.name] = file_hash(path)
        manifest["status"] = "complete"
    except Exception as exc:
        manifest["error"] = f"{type(exc).__name__}: {exc}"
        write_json(folder / "manifest.json", manifest)
        raise
    write_json(folder / "manifest.json", manifest)
    # Only complete acquisitions replace the pointer; earlier snapshots remain intact.
    latest = root / "data" / "LATEST"
    pending = latest.with_suffix(".tmp")
    pending.write_text(identifier + "\n", encoding="utf-8")
    pending.replace(latest)
    return folder


def resolve_snapshot(root: Path, identifier: str | None = None) -> Path:
    if identifier is None:
        pointer = root / "data" / "LATEST"
        if not pointer.exists():
            raise ValueError("No snapshot yet. Run with --download first.")
        identifier = pointer.read_text().strip()
    if not identifier or Path(identifier).name != identifier or identifier in {".", ".."}:
        raise ValueError("Snapshot must be a directory name, not a path")
    return root / "data" / "snapshots" / identifier


def load_snapshot(folder: Path) -> tuple[DataConfig, dict, dict[str, pd.DataFrame], pd.Series]:
    manifest = json.loads((folder / "manifest.json").read_text())
    if manifest.get("schema_version") != 1 or manifest.get("status") != "complete":
        raise ValueError("Snapshot is incomplete or has an unsupported schema")
    if manifest.get("snapshot_id") != folder.name:
        raise ValueError("Snapshot directory and manifest identity differ")
    settings = dict(manifest["config"])
    settings["tickers"] = tuple(settings["tickers"])
    config = DataConfig(**settings)
    expected = {f"{t}.csv" for t in config.tickers} | {"fred.csv"}
    if set(manifest["files"]) != expected:
        raise ValueError("Snapshot manifest does not match required inputs")
    for name, digest in manifest["files"].items():
        if file_hash(folder / name) != digest:
            raise ValueError(f"Snapshot integrity check failed: {name}")
    frames = {
        t: pd.read_csv(
            folder / f"{t}.csv", index_col="Date", parse_dates=True, float_precision="round_trip"
        )
        for t in config.tickers
    }
    rates = parse_fred((folder / "fred.csv").read_text(), config.risk_free_series)
    return config, manifest, frames, rates
