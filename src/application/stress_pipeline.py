"""Build comparable risk attribution, funded-transfer checks and stress replays offline."""

import json
from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from src.application.data_pipeline import build_data
from src.application.risk_pipeline import _git_state, _portfolios, _read_returns
from src.data.snapshots import file_hash, write_json
from src.domain.config import UNIVERSE, OptimisationConfig, RiskConfig, StressConfig
from src.models.contributions import (
    funded_transfer_checks,
    historical_es_contributions,
    normal_contributions,
)
from src.models.optimisation import fit_target_allocations
from src.models.risk import fit_gaussian, select_risk_window
from src.models.stress import historical_replay, joint_shock
from src.reporting.stress import plot_stress, render_stress_report


def build_stress(
    root: Path,
    snapshot: Path,
    risk: RiskConfig | None = None,
    stress: StressConfig | None = None,
    policy: OptimisationConfig | None = None,
    data_builder: Callable = build_data,
) -> Path:
    risk, stress, policy = (
        risk or RiskConfig(),
        stress or StressConfig(),
        policy or OptimisationConfig(),
    )
    settings = {
        "risk": {
            key: getattr(risk, key)
            for key in ("as_of", "lookback_observations", "confidence_levels", "reference_nav")
        },
        "stress": asdict(stress),
        "portfolio": asdict(policy),
    }
    run_id = sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:12]
    output = root / "output/stress" / snapshot.name / run_id
    output.mkdir(parents=True, exist_ok=True)
    status = {"snapshot_id": snapshot.name, "run_id": run_id, "status": "building"}
    write_json(output / "status.json", status)
    try:
        prepared = data_builder(root, snapshot)
        all_returns = _read_returns(prepared / "simple_returns.csv")
        window = select_risk_window(all_returns, risk)
        if tuple(window.columns) != UNIVERSE:
            raise ValueError("Stress analysis requires all seven eligible ETFs")
        expected = xcals.get_calendar(
            "XNYS", start=window.index[0], end=window.index[-1]
        ).sessions.tz_localize(None)
        if not window.index.equals(expected):
            raise ValueError("Attribution window must contain consecutive exchange sessions")
        as_of = window.index[-1]
        if as_of < pd.Timestamp(policy.development_end_exclusive):
            raise ValueError("As-of precedes the frozen allocation cutoff")
        observed = all_returns.loc[:as_of]
        rates = _read_returns(prepared / "risk_free_returns.csv").simple_return.loc[:as_of]
        development = observed.loc[observed.index < policy.development_end_exclusive]
        development_rates = rates.reindex(development.index)
        fitted = fit_target_allocations(development, development_rates, policy)
        portfolios = _portfolios(fitted.candidates, policy)
        weights_as_of = str(development.index[-1].date())
        totals, details, transfers, historical, paths, terminal, shocks, shock_parts = (
            [],
            [],
            [],
            [],
            [],
            [],
            [],
            [],
        )
        for strategy, weights in portfolios.items():
            for confidence in risk.confidence_levels:
                estimates = (
                    *normal_contributions(window, weights, confidence),
                    historical_es_contributions(window, weights, confidence),
                )
                for result in estimates:
                    identity = {
                        "strategy": strategy,
                        "method": result.method,
                        "measure": result.measure,
                        "confidence": confidence,
                    }
                    components = [a.component_fraction for a in result.assets]
                    component_sum = (
                        float(sum(components)) if all(x is not None for x in components) else None
                    )
                    if component_sum is not None and not np.isclose(
                        component_sum, result.total_fraction, atol=1e-12, rtol=1e-10
                    ):
                        raise RuntimeError("Risk components fail to sum to portfolio risk")
                    totals.append(
                        dict(
                            **identity,
                            total_fraction=result.total_fraction,
                            total_percent=100 * result.total_fraction,
                            total_usd=risk.reference_nav * result.total_fraction,
                            component_sum_fraction=component_sum,
                            reconciliation_error_fraction=component_sum - result.total_fraction
                            if component_sum is not None
                            else None,
                            status=result.status,
                            warning=result.warning,
                            effective_tail_observations=result.effective_tail_observations,
                            es_review_level=stress.es_review_level
                            if result.measure == "es" and np.isclose(confidence, 0.99)
                            else None,
                            es_review_trigger_breached=bool(
                                result.total_fraction > stress.es_review_level
                            )
                            if result.measure == "es" and np.isclose(confidence, 0.99)
                            else None,
                        )
                    )
                    for asset in result.assets:
                        details.append(
                            dict(
                                **identity,
                                **asdict(asset),
                                component_usd=risk.reference_nav * asset.component_fraction
                                if asset.component_fraction is not None
                                else None,
                                component_percent=100 * asset.component_fraction
                                if asset.component_fraction is not None
                                else None,
                                marginal_usd_per_one_pp=0.01
                                * risk.reference_nav
                                * asset.marginal_fraction
                                if asset.marginal_fraction is not None
                                else None,
                            )
                        )
                transfer = funded_transfer_checks(
                    window, weights, confidence, stress.transfer_weight, policy
                )
                transfer.insert(0, "strategy", strategy)
                for column in ("before", "after", "delta", "linear_delta"):
                    transfer[f"{column}_usd"] = transfer[f"{column}_fraction"] * risk.reference_nav
                transfers.append(transfer)
            for period in stress.historical_periods:
                run = historical_replay(
                    observed,
                    weights,
                    period,
                    risk.reference_nav,
                    strategy,
                    weights_as_of,
                    stress.drawdown_review_level,
                )
                historical.append(asdict(run.summary))
                if not run.path.empty:
                    paths.append(
                        run.path.reset_index().assign(strategy=strategy, scenario=period.name)
                    )
                    terminal.append(run.components.assign(strategy=strategy, scenario=period.name))
            for multiplier in stress.shock_multipliers:
                run = joint_shock(
                    weights,
                    pd.Series(dict(stress.shocks)),
                    risk.reference_nav,
                    strategy,
                    stress.shock_name,
                    multiplier,
                    stress.shock_review_level,
                )
                shocks.append(asdict(run.summary))
                shock_parts.append(
                    run.components.assign(
                        strategy=strategy, scenario=stress.shock_name, multiplier=multiplier
                    )
                )
        frames = {
            "contribution_summary": pd.DataFrame(totals),
            "asset_contributions": pd.DataFrame(details),
            "sizing_checks": pd.concat(transfers, ignore_index=True),
            "historical_summary": pd.DataFrame(historical),
            "historical_paths": pd.concat(paths, ignore_index=True)
            if paths
            else pd.DataFrame(columns=["Date", "strategy", "scenario", "nav", "drawdown_fraction"]),
            "historical_components": pd.concat(terminal, ignore_index=True)
            if terminal
            else pd.DataFrame(columns=["ticker", "strategy", "scenario", "terminal_loss_usd"]),
            "hypothetical_summary": pd.DataFrame(shocks),
            "hypothetical_components": pd.concat(shock_parts, ignore_index=True),
            "scenario_shocks": pd.DataFrame(
                {
                    "ticker": UNIVERSE,
                    "base_shock_return": [v for _, v in stress.shocks],
                    "development_worst_daily_return": development.min()
                    .reindex(UNIVERSE)
                    .to_numpy(),
                }
            ),
        }
        for name, frame in frames.items():
            frame.to_csv(output / f"{name}.csv", index=False, float_format="%.17g")
        pd.DataFrame(portfolios).T.to_csv(
            output / "portfolio_weights.csv", index_label="strategy", float_format="%.17g"
        )
        window.to_csv(output / "estimation_returns.csv", index_label="Date", float_format="%.17g")
        replay_inputs = [
            observed.loc[(observed.index >= p.start) & (observed.index < p.end_exclusive)].assign(
                scenario=p.name
            )
            for p in stress.historical_periods
        ]
        pd.concat(replay_inputs).to_csv(
            output / "stress_returns.csv", index_label="Date", float_format="%.17g"
        )
        moments = fit_gaussian(window)
        moments.mean.to_csv(
            output / "asset_means.csv",
            header=["daily_mean"],
            index_label="ticker",
            float_format="%.17g",
        )
        moments.covariance.to_csv(output / "asset_covariance.csv", float_format="%.17g")
        context = {
            "snapshot_id": snapshot.name,
            "run_id": run_id,
            "as_of": str(as_of.date()),
            "window_start": str(window.index[0].date()),
            "observations": len(window),
            "reference_nav": risk.reference_nav,
            "weights_as_of": weights_as_of,
            "shock_narrative": stress.shock_narrative,
            "transfer_weight": stress.transfer_weight,
            "es_review_level": stress.es_review_level,
            "drawdown_review_level": stress.drawdown_review_level,
            "shock_review_level": stress.shock_review_level,
        }
        forecast_sessions = xcals.get_calendar(
            "XNYS", start=as_of, end=as_of + pd.Timedelta(days=14)
        ).sessions.tz_localize(None)
        context["forecast_session"] = str(forecast_sessions[forecast_sessions > as_of][0].date())
        charts = plot_stress(frames, output)
        (output / "stress_report.md").write_text(
            render_stress_report(frames, context, charts), encoding="utf-8"
        )
        source_root = Path(__file__).resolve().parents[2]
        sources = sorted((source_root / "src").rglob("*.py")) + [source_root / "run_stress.py"]
        write_json(
            output / "summary.json",
            dict(
                **context,
                config=settings,
                git=_git_state(source_root),
                review_record="docs/final/08-contributions-stress/03-manual-stress-check.md",
                human_validation="pending",
                scenario_approval="proposed; team interpretation pending",
                replay_basis="fixed initial allocation, buy and hold, no fees or withdrawals; retrospective replay",
                marginal_basis="unconstrained exposure derivative; funded transfers explicitly repriced",
                risk_horizon_sessions=1,
                manifest_sha256=file_hash(snapshot / "manifest.json"),
                development_returns_sha256=sha256(
                    development.to_csv(float_format="%.17g").encode()
                ).hexdigest(),
                development_rates_sha256=sha256(
                    development_rates.to_csv(float_format="%.17g").encode()
                ).hexdigest(),
                dependency_lock_sha256=file_hash(source_root / "uv.lock"),
                packages={
                    p: version(p)
                    for p in ("numpy", "pandas", "scipy", "matplotlib", "exchange-calendars")
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
    write_json(
        output / "status.json",
        dict(status, status="complete", human_validation="see manual worksheet"),
    )
    return output
