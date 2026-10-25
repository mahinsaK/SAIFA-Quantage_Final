"""Reproduce target allocations, then estimate comparable one-day market losses."""

import json
import subprocess
from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

from saifa.application.data_pipeline import build_data
from saifa.data.snapshots import file_hash, write_json, write_output_manifest
from saifa.domain.config import UNIVERSE, OptimisationConfig, RiskConfig
from saifa.domain.portfolio import OptimisationResult
from saifa.models.optimisation import fit_target_allocations, validate_policy_weights
from saifa.models.risk import compare_risk, fit_gaussian, ordered_weights, select_risk_window
from saifa.reporting.risk import render_risk_report


def _read_returns(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col="Date", parse_dates=True, float_precision="round_trip")


def _portfolios(
    candidates: tuple[OptimisationResult, ...], policy: OptimisationConfig
) -> dict[str, pd.Series]:
    expected = {"minimum_volatility", "maximum_sharpe"}
    if (
        len(candidates) != 2
        or {r.name for r in candidates} != expected
        or not all(r.success for r in candidates)
    ):
        raise ValueError("Exactly two successful optimized candidates are required")
    portfolios = {"baseline_40_60": pd.Series(0.0, index=UNIVERSE)}
    portfolios["baseline_40_60"].loc[["SPY", "AGG"]] = [0.4, 0.6]
    for result in candidates:
        weights = result.weights
        validate_policy_weights(weights, policy)
        ordered_weights(weights, pd.Index(UNIVERSE))
        portfolios[result.name] = weights
    return portfolios


def _git_state(root: Path) -> dict:
    try:
        revision = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        return {"revision": revision, "working_tree_dirty": bool(dirty)}
    except (OSError, subprocess.CalledProcessError):
        return {"revision": None, "working_tree_dirty": None}


def build_risk(
    root: Path,
    snapshot: Path,
    config: RiskConfig | None = None,
    policy: OptimisationConfig | None = None,
    data_builder: Callable = build_data,
) -> Path:
    config = config or RiskConfig()
    policy = policy or OptimisationConfig()
    settings = {"risk": asdict(config), "portfolio": asdict(policy)}
    run_id = sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:12]
    output = root / "output" / "risk" / snapshot.name / run_id
    output.mkdir(parents=True, exist_ok=True)
    status = {"snapshot_id": snapshot.name, "run_id": run_id, "status": "building"}
    write_json(output / "status.json", status)
    try:
        # Rebuild from verified inputs; never silently trust a stale candidate CSV.
        data_output = data_builder(root, snapshot)
        returns_path = data_output / "simple_returns.csv"
        asset_returns = _read_returns(returns_path)
        window = select_risk_window(asset_returns, config)
        if tuple(window.columns) != UNIVERSE:
            raise ValueError("Risk comparison requires all seven eligible ETFs")
        as_of = window.index[-1]
        if as_of < pd.Timestamp(policy.development_end_exclusive):
            raise ValueError("As-of date precedes the frozen portfolio estimation cutoff")
        rates = _read_returns(data_output / "risk_free_returns.csv").simple_return
        fit = fit_target_allocations(asset_returns.loc[:as_of], rates.loc[:as_of], policy)
        portfolios = _portfolios(fit.candidates, policy)
        results = pd.DataFrame([asdict(r) for r in compare_risk(window, portfolios, config)])
        sessions = xcals.get_calendar(
            "XNYS", start=as_of, end=as_of + pd.Timedelta(days=14)
        ).sessions.tz_localize(None)
        forecast_session = sessions[sessions > as_of][0]
        all_dates = asset_returns.index
        estimation_last_date = all_dates[all_dates < policy.development_end_exclusive][-1]
        context = {
            "snapshot_id": snapshot.name,
            "as_of": str(as_of.date()),
            "forecast_session": str(forecast_session.date()),
            "window_start": str(window.index[0].date()),
            "observations": len(window),
            "reference_nav": config.reference_nav,
            "simulations": config.simulations,
            "seed": config.seed,
            "weights_estimation_last_date": str(estimation_last_date.date()),
        }
        results.insert(0, "as_of", context["as_of"])
        results.insert(1, "forecast_session", context["forecast_session"])
        results.insert(2, "window_start", context["window_start"])
        results.to_csv(output / "risk_estimates.csv", index=False, float_format="%.17g")
        pd.DataFrame(portfolios).T.rename_axis("strategy").to_csv(
            output / "portfolio_weights.csv", float_format="%.17g"
        )
        window.to_csv(output / "estimation_returns.csv", index_label="Date", float_format="%.17g")
        fit = fit_gaussian(window)
        fit.mean.rename("daily_mean").to_csv(
            output / "asset_means.csv", index_label="ticker", float_format="%.17g"
        )
        fit.covariance.to_csv(output / "asset_covariance.csv", float_format="%.17g")
        (output / "risk_report.md").write_text(
            render_risk_report(results, context), encoding="utf-8"
        )
        source_root = Path(__file__).resolve().parents[3]
        source_files = sorted((source_root / "src/saifa").rglob("*.py")) + [
            source_root / "commands/run_risk.py"
        ]
        summary = {
            **context,
            "run_id": run_id,
            "config": settings,
            "git": _git_state(source_root),
            "weight_basis": "frozen_target_allocations",
            "loss_convention": "negative simple portfolio return; positive means loss",
            "human_validation": "pending",
            "coverage_backtest": "not_implemented",
            "snapshot_manifest_sha256": file_hash(snapshot / "manifest.json"),
            "portfolio_weights_sha256": file_hash(output / "portfolio_weights.csv"),
            "dependency_lock_sha256": file_hash(source_root / "uv.lock"),
            "packages": {name: version(name) for name in ("numpy", "pandas", "scipy")},
            "code_sha256": {str(p.relative_to(source_root)): file_hash(p) for p in source_files},
            "outputs_sha256": {
                p.name: file_hash(p)
                for p in sorted(output.iterdir())
                if p.suffix in {".csv", ".md"}
            },
        }
        write_json(output / "summary.json", summary)
    except Exception as exc:
        status.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        write_json(output / "status.json", status)
        write_output_manifest(output, snapshot.name, run_id)
        raise
    status.update(status="complete", human_validation="pending")
    write_json(output / "status.json", status)
    write_output_manifest(output, snapshot.name, run_id)
    return output
