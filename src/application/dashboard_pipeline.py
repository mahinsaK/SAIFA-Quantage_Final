"""Prepare one explicit, hash-verified app bundle using the existing offline pipelines."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from src.application.backtest_pipeline import build_backtest
from src.application.evt_pipeline import build_evt
from src.application.optimisation_pipeline import build_optimised_portfolios
from src.application.stress_pipeline import build_stress
from src.data.snapshots import file_hash, write_json
from src.domain.config import BacktestConfig, RiskConfig
from src.domain.dashboard import CONFIDENCES, TABLES


def publish_bundle(root: Path, snapshot: Path, outputs: dict[str, Path]) -> Path:
    from src.dashboard.data import load_bundle

    path = root / "output/app" / snapshot.name / "bundle.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": 1,
        "status": "complete",
        "snapshot_id": snapshot.name,
        "snapshot_manifest_sha256": file_hash(snapshot / "manifest.json"),
        "prepared_at_utc": datetime.now(UTC).isoformat(),
        "stages": {},
    }
    for stage, tables in TABLES.items():
        folder = outputs[stage]
        files = ["status.json", "summary.json", *[f"{table}.csv" for table in tables]]
        manifest["stages"][stage] = {
            "path": str(folder.relative_to(root)),
            "files": {name: file_hash(folder / name) for name in files},
        }
    # Validate a candidate before atomically publishing it as the active bundle.
    pending = path.with_name("bundle.pending.json")
    write_json(pending, manifest)
    load_bundle(root, pending)
    pending.replace(path)
    return path


def build_dashboard(root: Path, snapshot: Path, progress=print) -> Path:
    path = root / "output/app" / snapshot.name / "bundle.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(path, {"schema_version": 1, "status": "building", "snapshot_id": snapshot.name})
    try:
        progress("Preparing monthly-rebalanced portfolio performance...")
        portfolio = build_optimised_portfolios(root, snapshot)
        risk_config = replace(RiskConfig(), confidence_levels=CONFIDENCES)
        progress("Preparing 90/95/99% risk estimates and EVT diagnostics...")
        risk = build_evt(root, snapshot, risk=risk_config)
        progress("Preparing risk contributions and stress scenarios...")
        stress = build_stress(root, snapshot, risk=risk_config)
        progress("Preparing 90/95/99% walk-forward forecasts; this can take several minutes...")
        backtest = build_backtest(
            root,
            snapshot,
            config=replace(BacktestConfig(), confidence_levels=CONFIDENCES),
            progress=lambda n, total: progress(f"Forecast sessions: {n}/{total}"),
        )
        path = publish_bundle(
            root,
            snapshot,
            {
                "portfolio": portfolio,
                "risk": risk,
                "stress": stress,
                "backtest": backtest,
                "data": root / "output/data" / snapshot.name,
            },
        )
        progress("App bundle verified and ready.")
        return path
    except Exception as exc:
        write_json(
            path,
            {
                "schema_version": 1,
                "status": "failed",
                "snapshot_id": snapshot.name,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise
