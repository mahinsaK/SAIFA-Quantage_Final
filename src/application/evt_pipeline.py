"""Offline EVT study with fixed threshold rule, diagnostic provenance and uncertainty."""

import json
from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

from src.application.data_pipeline import build_data
from src.application.risk_pipeline import _git_state, _portfolios, _read_returns
from src.data.snapshots import file_hash, write_json
from src.domain.config import UNIVERSE, EVTConfig, OptimisationConfig, RiskConfig
from src.models.evt import (
    bootstrap_intervals,
    bootstrap_tail,
    pot_tail,
    qq_diagnostics,
    threshold_diagnostics,
)
from src.models.optimisation import fit_target_allocations
from src.models.risk import compare_risk, fit_gaussian, select_risk_window
from src.reporting.evt import plot_diagnostics, render_evt_report


def build_evt(
    root: Path,
    snapshot: Path,
    risk: RiskConfig | None = None,
    evt: EVTConfig | None = None,
    policy: OptimisationConfig | None = None,
    data_builder: Callable = build_data,
) -> Path:
    risk, evt, policy = risk or RiskConfig(), evt or EVTConfig(), policy or OptimisationConfig()
    settings = {"risk": asdict(risk), "evt": asdict(evt), "portfolio": asdict(policy)}
    run_id = sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:12]
    output = root / "output" / "evt" / snapshot.name / run_id
    output.mkdir(parents=True, exist_ok=True)
    status = {"snapshot_id": snapshot.name, "run_id": run_id, "status": "building"}
    write_json(output / "status.json", status)
    try:
        data_output = data_builder(root, snapshot)
        returns = _read_returns(data_output / "simple_returns.csv")
        window = select_risk_window(returns, risk)
        if tuple(window.columns) != UNIVERSE:
            raise ValueError("EVT comparison requires all seven eligible ETFs")
        fit_gaussian(window)  # Validate finite simple returns and column integrity.
        as_of = window.index[-1]
        if as_of < pd.Timestamp(policy.development_end_exclusive):
            raise ValueError("As-of date precedes the frozen portfolio estimation cutoff")
        rates = _read_returns(data_output / "risk_free_returns.csv").simple_return
        fitted = fit_target_allocations(returns.loc[:as_of], rates.loc[:as_of], policy)
        portfolios = _portfolios(fitted.candidates, policy)
        development = returns.loc[returns.index < policy.development_end_exclusive]
        fit_gaussian(development)
        diagnostics, sensitivity, estimates, qq_rows, boot_rows = [], [], [], [], []
        for strategy, weights in portfolios.items():
            for period, frame in (("development", development), ("as_of", window)):
                losses = -(frame @ weights).to_numpy()
                fits = threshold_diagnostics(losses, evt)
                for fit in fits:
                    diagnostics.append(
                        dict(
                            strategy=strategy,
                            period=period,
                            start=str(frame.index[0].date()),
                            end=str(frame.index[-1].date()),
                            **asdict(fit),
                        )
                    )
                    for confidence in risk.confidence_levels:
                        sensitivity.append(
                            dict(
                                strategy=strategy,
                                period=period,
                                quantile=fit.quantile,
                                **asdict(pot_tail(fit, confidence)),
                            )
                        )
                selected = next(f for f in fits if f.quantile == evt.threshold_quantile)
                qq = qq_diagnostics(losses, selected)
                qq.insert(0, "period", period)
                qq.insert(0, "strategy", strategy)
                qq_rows.append(qq)
                if period == "as_of":
                    draws = bootstrap_tail(losses, evt, risk.confidence_levels)
                    draws.insert(0, "strategy", strategy)
                    boot_rows.append(draws)
                    for confidence in risk.confidence_levels:
                        tail = pot_tail(selected, confidence)
                        row = dict(
                            strategy=strategy,
                            method="evt_pot_gpd",
                            as_of=str(as_of.date()),
                            confidence=confidence,
                            horizon_sessions=1,
                            reference_nav=risk.reference_nav,
                            observations=len(frame),
                            threshold_quantile=selected.quantile,
                            threshold=selected.threshold,
                            exceedances=selected.exceedances,
                            shape=selected.shape,
                            scale=selected.scale,
                            **{k: v for k, v in asdict(tail).items() if k != "confidence"},
                            **bootstrap_intervals(draws, tail),
                        )
                        for measure in ("var", "es"):
                            value = row[f"{measure}_fraction"]
                            row[f"{measure}_percent"] = 100 * value if value is not None else None
                            row[f"{measure}_usd"] = (
                                risk.reference_nav * value if value is not None else None
                            )
                        estimates.append(row)
        diagnostics = pd.DataFrame(diagnostics)
        sensitivity = pd.DataFrame(sensitivity)
        estimates = pd.DataFrame(estimates)
        qq = pd.concat(qq_rows, ignore_index=True)
        sessions = xcals.get_calendar(
            "XNYS", start=as_of, end=as_of + pd.Timedelta(days=14)
        ).sessions.tz_localize(None)
        context = {
            "snapshot_id": snapshot.name,
            "run_id": run_id,
            "as_of": str(as_of.date()),
            "forecast_session": str(sessions[sessions > as_of][0].date()),
            "window_start": str(window.index[0].date()),
            "observations": len(window),
            "development_start": str(development.index[0].date()),
            "development_end": str(development.index[-1].date()),
            "reference_nav": risk.reference_nav,
            "threshold_quantile": evt.threshold_quantile,
            "block_length": evt.block_length,
            "bootstrap_replicates": evt.bootstrap_replicates,
            "seed": evt.seed,
        }
        estimates.insert(2, "forecast_session", context["forecast_session"])
        estimates.insert(3, "window_start", context["window_start"])
        comparison = pd.DataFrame([asdict(r) for r in compare_risk(window, portfolios, risk)])
        comparison["status"] = "ok"
        comparison = pd.concat([comparison, estimates], ignore_index=True)
        comparison["as_of"] = context["as_of"]
        comparison["forecast_session"] = context["forecast_session"]
        comparison["window_start"] = context["window_start"]
        tables = {
            "evt_estimates": estimates,
            "threshold_diagnostics": diagnostics,
            "threshold_sensitivity": sensitivity,
            "qq_diagnostics": qq,
            "bootstrap_draws": pd.concat(boot_rows, ignore_index=True),
            "risk_comparison": comparison,
        }
        for name, table in tables.items():
            table.to_csv(output / f"{name}.csv", index=False, float_format="%.17g")
        pd.DataFrame(portfolios).T.to_csv(
            output / "portfolio_weights.csv", index_label="strategy", float_format="%.17g"
        )
        window.to_csv(output / "estimation_returns.csv", index_label="Date", float_format="%.17g")
        plot_diagnostics(diagnostics, sensitivity, qq, output, evt.threshold_quantile)
        (output / "evt_report.md").write_text(
            render_evt_report(estimates, diagnostics, context), encoding="utf-8"
        )
        source_root = Path(__file__).resolve().parents[2]
        sources = sorted((source_root / "src").rglob("*.py")) + [source_root / "run_evt.py"]
        write_json(
            output / "summary.json",
            dict(
                **context,
                config=settings,
                git=_git_state(source_root),
                threshold_rule="prespecified_quantile; no automatic selection from evaluation results",
                threshold_approval="pending human diagnostic review",
                human_validation="pending",
                coverage_backtest="not_implemented",
                weight_basis="frozen_target_allocations",
                uncertainty="95% circular-block percentile intervals; rule fixed, threshold refitted",
                snapshot_manifest_sha256=file_hash(snapshot / "manifest.json"),
                development_returns_sha256=sha256(
                    development.to_csv(float_format="%.17g").encode()
                ).hexdigest(),
                dependency_lock_sha256=file_hash(source_root / "uv.lock"),
                packages={
                    name: version(name) for name in ("numpy", "pandas", "scipy", "matplotlib")
                },
                code_sha256={str(p.relative_to(source_root)): file_hash(p) for p in sources},
                outputs_sha256={
                    p.name: file_hash(p)
                    for p in sorted(output.iterdir())
                    if p.suffix in {".csv", ".md", ".png"}
                },
            ),
        )
    except Exception as exc:
        write_json(
            output / "status.json",
            dict(status, status="failed", error=f"{type(exc).__name__}: {exc}"),
        )
        raise
    write_json(output / "status.json", dict(status, status="complete", human_validation="pending"))
    return output
