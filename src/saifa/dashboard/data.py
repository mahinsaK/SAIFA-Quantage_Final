"""Verify explicitly published outputs before caching or displaying them."""

import json
from hashlib import sha256
from pathlib import Path

import numpy as np
import pandas as pd

from saifa.data.snapshots import file_hash
from saifa.domain.config import UNIVERSE
from saifa.domain.dashboard import (
    CONFIDENCES,
    METHODS,
    STRATEGIES,
    TABLES,
    DashboardBundle,
    DashboardDataError,
)


def read_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise TypeError("Expected an object")
        return value
    except (OSError, ValueError, TypeError) as exc:
        raise DashboardDataError(f"Cannot read {path.name}: {exc}") from exc


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise DashboardDataError("Result path must stay inside the project")
    return path


def verify_bundle(root: Path, manifest_path: Path) -> str:
    """Called on EVERY rerun, even if parsed tables are cached. Missing/stale files fail closed."""
    manifest = read_json(manifest_path)
    if manifest.get("schema_version") != 1 or manifest.get("status") != "complete":
        raise DashboardDataError(
            f"App results are {manifest.get('status', 'unavailable')}. Rebuild them."
        )
    snapshot_id = manifest.get("snapshot_id", "")
    if not snapshot_id or Path(snapshot_id).name != snapshot_id or snapshot_id in {".", ".."}:
        raise DashboardDataError("Invalid snapshot identity")
    snapshot = root / "data/snapshots" / snapshot_id
    source = read_json(snapshot / "manifest.json")
    if source.get("status") != "complete" or source.get("snapshot_id") != snapshot_id:
        raise DashboardDataError("Source snapshot is incomplete or has a different identity")
    try:
        if set(source["files"]) != {f"{t}.csv" for t in UNIVERSE} | {"fred.csv"}:
            raise DashboardDataError("Snapshot does not contain the seven ETFs and FRED input")
        if file_hash(snapshot / "manifest.json") != manifest["snapshot_manifest_sha256"]:
            raise DashboardDataError("Snapshot manifest changed; rebuild app results")
        for name, digest in source["files"].items():
            if file_hash(inside(snapshot, name)) != digest:
                raise DashboardDataError(f"Snapshot input changed: {name}")
        if set(manifest["stages"]) != set(TABLES):
            raise DashboardDataError("App bundle is missing a required analysis")
        for stage, tables in TABLES.items():
            entry = manifest["stages"][stage]
            folder = inside(root, entry["path"])
            required = {"status.json", "summary.json"} | {f"{t}.csv" for t in tables}
            if set(entry["files"]) != required:
                raise DashboardDataError(f"{stage}: incomplete file manifest")
            for name, digest in entry["files"].items():
                if file_hash(folder / name) != digest:
                    raise DashboardDataError(f"{stage}/{name} changed; rebuild the app bundle")
            status, summary = read_json(folder / "status.json"), read_json(folder / "summary.json")
            if status.get("status") != "complete":
                raise DashboardDataError(f"{stage}: results are not complete")
            if (
                status.get("snapshot_id") != snapshot_id
                or summary.get("snapshot_id") != snapshot_id
            ):
                raise DashboardDataError(f"{stage}: snapshot identity mismatch")
    except (OSError, KeyError, TypeError) as exc:
        raise DashboardDataError(f"App bundle is missing a required file or field: {exc}") from exc
    return sha256(manifest_path.read_bytes()).hexdigest()


def load_bundle(root: Path, manifest_path: Path) -> DashboardBundle:
    verify_bundle(root, manifest_path)
    manifest = read_json(manifest_path)
    metadata, frames = {}, {}
    try:
        for stage, tables in TABLES.items():
            folder = inside(root, manifest["stages"][stage]["path"])
            metadata[stage] = read_json(folder / "summary.json")
            frames[stage] = {
                name: pd.read_csv(folder / f"{name}.csv", float_precision="round_trip")
                for name in tables
            }
        bundle = DashboardBundle(manifest_path, manifest, metadata, frames)
        validate_tables(bundle)
        return bundle
    except (KeyError, ValueError, TypeError, AttributeError, OSError) as exc:
        raise DashboardDataError(f"Result tables cannot be used: {exc}") from exc


def _grid(frame: pd.DataFrame, keys: list[str], expected: pd.MultiIndex) -> None:
    actual = pd.MultiIndex.from_frame(frame[keys])
    if actual.has_duplicates or len(actual) != len(expected) or set(actual) != set(expected):
        raise DashboardDataError(f"Missing/duplicate result rows for {keys}")


def validate_tables(bundle: DashboardBundle) -> None:
    """Protect comparisons from mixed settings, missing confidence rows and incompatible units."""
    tables, meta = bundle.tables, bundle.metadata
    risk = tables["risk"]["risk_comparison"]
    _grid(
        risk,
        ["strategy", "method", "confidence"],
        pd.MultiIndex.from_product([STRATEGIES, METHODS, CONFIDENCES]),
    )
    for field in ("as_of", "forecast_session", "window_start", "observations", "reference_nav"):
        if (
            risk[field].isna().any()
            or risk[field].nunique() != 1
            or risk[field].iloc[0] != meta["risk"][field]
        ):
            raise DashboardDataError(f"Inconsistent risk {field}")
    if not (risk.horizon_sessions == 1).all():
        raise DashboardDataError("Only one-session risk can be compared")
    for measure in ("var", "es"):
        fractions = risk[f"{measure}_fraction"].to_numpy(dtype=float)
        for suffix, factor in (("usd", meta["risk"]["reference_nav"]), ("percent", 100)):
            if not np.allclose(risk[f"{measure}_{suffix}"], fractions * factor, equal_nan=True):
                raise DashboardDataError(f"Inconsistent risk {measure} {suffix} units")
        if np.isinf(fractions).any():
            raise DashboardDataError("Infinite risk must be unavailable")
    if risk.loc[risk.status == "ok", ["var_fraction", "es_fraction"]].isna().any().any():
        raise DashboardDataError("Successful risk row has missing values")
    for field in ("as_of", "window_start", "observations", "reference_nav"):
        if meta["stress"][field] != meta["risk"][field]:
            raise DashboardDataError(f"Stress attribution has different {field}")
    policy = meta["portfolio"]["config"]
    for stage in ("risk", "stress", "backtest"):
        if meta[stage]["config"]["portfolio"] != policy:
            raise DashboardDataError(f"{stage}: different portfolio policy")
    weights = (
        tables["risk"]["portfolio_weights"]
        .set_index("strategy")
        .loc[list(STRATEGIES), list(UNIVERSE)]
    )
    other = (
        tables["stress"]["portfolio_weights"]
        .set_index("strategy")
        .loc[list(STRATEGIES), list(UNIVERSE)]
    )
    if not np.allclose(weights, other, atol=1e-10) or not np.allclose(weights.sum(axis=1), 1):
        raise DashboardDataError("Allocation weights do not match")
    candidates = tables["portfolio"]["candidate_weights"].set_index("strategy")
    for strategy in ("minimum_volatility", "maximum_sharpe"):
        if not np.allclose(
            weights.loc[strategy],
            candidates.loc[strategy, [f"weight_{t}" for t in UNIVERSE]].astype(float),
        ):
            raise DashboardDataError("Performance and risk use different candidate weights")
    f = tables["backtest"]["forecasts"]
    keys = ["strategy", "method", "confidence", "forecast_date"]
    if f.duplicated(keys).any():
        raise DashboardDataError("Duplicate dated forecast")
    _grid(
        f[["strategy", "method", "confidence"]].drop_duplicates(),
        ["strategy", "method", "confidence"],
        pd.MultiIndex.from_product([STRATEGIES, METHODS, CONFIDENCES]),
    )
    if not (pd.to_datetime(f.as_of) < pd.to_datetime(f.forecast_date)).all():
        raise DashboardDataError("Forecast uses its target date or future information")
    if (
        not (f.reference_nav == meta["risk"]["reference_nav"]).all()
        or not (f.horizon_sessions == 1).all()
    ):
        raise DashboardDataError("Backtest NAV/horizon differs from risk comparison")
    if not (pd.to_datetime(f.weights_as_of) <= pd.to_datetime(f.as_of)).all():
        raise DashboardDataError("Forecast uses future allocation weights")
    for measure in ("var", "loss"):
        if not np.allclose(
            f[f"{measure}_usd"],
            f[f"{measure}_fraction"] * f.reference_nav,
            equal_nan=True,
            rtol=1e-10,
            atol=1e-8,
        ):
            raise DashboardDataError(f"Inconsistent forecast {measure} units")
    for frame in (
        tables["portfolio"]["evaluation_daily"],
        tables["portfolio"]["evaluation_metrics"],
    ):
        if set(frame.strategy) != set(STRATEGIES):
            raise DashboardDataError("Missing portfolio performance")
    daily = tables["portfolio"]["evaluation_daily"]
    if daily.duplicated(["strategy", "Date"]).any() or not np.isfinite(daily.nav).all():
        raise DashboardDataError("Portfolio path has duplicate dates or missing NAV")
    totals = tables["stress"]["contribution_summary"]
    expected = [
        (s, m, measure, c)
        for s in STRATEGIES
        for c in CONFIDENCES
        for m, measure in (
            ("historical", "es"),
            ("parametric_normal", "var"),
            ("parametric_normal", "es"),
        )
    ]
    _grid(
        totals, ["strategy", "method", "measure", "confidence"], pd.MultiIndex.from_tuples(expected)
    )
    history = tables["stress"]["historical_summary"]
    _grid(
        history,
        ["strategy", "scenario"],
        pd.MultiIndex.from_product([STRATEGIES, history.scenario.unique()]),
    )
    paths = tables["stress"]["historical_paths"]
    for row in history.itertuples():
        if (
            row.status == "ok"
            and paths.loc[(paths.strategy == row.strategy) & (paths.scenario == row.scenario)].empty
        ):
            raise DashboardDataError("Successful crisis replay is missing its path")
    shocks = tables["stress"]["hypothetical_summary"]
    _grid(
        shocks,
        ["strategy", "multiplier"],
        pd.MultiIndex.from_product([STRATEGIES, shocks.multiplier.unique()]),
    )
