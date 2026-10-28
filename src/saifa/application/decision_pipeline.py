"""Create traceable committee evidence from an already verified dashboard bundle."""

import subprocess
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from saifa.dashboard.data import load_bundle
from saifa.dashboard.selections import backtest_view
from saifa.data.inflation import load_frozen_cpi
from saifa.data.snapshots import file_hash, write_json
from saifa.domain.config import BacktestConfig
from saifa.domain.dashboard import CONFIDENCES, METHODS, STRATEGIES, DashboardBundle
from saifa.domain.decision import (
    CONDITIONS,
    CPI_LIMITATION,
    DECISION,
    INFLATION_SCENARIOS,
    REAL_CAPITAL_OBJECTIVE,
    WITHDRAWAL_RATE,
)
from saifa.models.observed_real import observed_real_growth
from saifa.models.spending import simulate_spending


def git_provenance(root: Path) -> tuple[str | None, bool | None]:
    """A ZIP without .git remains runnable; source hashes still identify its inputs."""
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, check=False
        )
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None, None
    if head.returncode or status.returncode:
        return None, None
    return head.stdout.strip(), bool(status.stdout.strip())


def decision_tables(bundle: DashboardBundle, cpi: pd.Series) -> dict[str, pd.DataFrame]:
    """No selection using the final-period winner; retain all methods and confidences."""
    meta = bundle.metadata
    config = BacktestConfig(**meta["backtest"]["config"]["backtest"])
    tests, lights = [], []
    for strategy in STRATEGIES:
        for method in METHODS:
            for confidence in CONFIDENCES:
                view = backtest_view(
                    bundle.tables["backtest"]["forecasts"],
                    strategy,
                    method,
                    confidence,
                    meta["backtest"]["start"],
                    meta["backtest"]["end"],
                    config,
                    meta["backtest"]["validation_end_exclusive"],
                )
                identity = {"strategy": strategy, "method": method, "confidence": confidence}
                tests.append(view.tests.assign(**identity))
                lights.append(view.lights.assign(**identity))
    policy = meta["portfolio"]["config"]
    daily = bundle.tables["portfolio"]["evaluation_daily"]
    summaries, paths, payments, observed = [], [], [], []
    for strategy in STRATEGIES:
        selected = daily.loc[daily.strategy == strategy].set_index("Date")
        observed.append(
            asdict(
                observed_real_growth(
                    strategy,
                    selected,
                    cpi,
                    policy["initial_capital"],
                    REAL_CAPITAL_OBJECTIVE,
                    meta["risk"]["as_of"],
                )
            )
        )
        for inflation in INFLATION_SCENARIOS:
            result = simulate_spending(
                selected,
                policy["initial_capital"],
                policy["transaction_cost_bps"] / 10000,
                inflation,
                WITHDRAWAL_RATE,
                REAL_CAPITAL_OBJECTIVE,
            )
            summaries.append(dict(strategy=strategy, **result.summary))
            identity = {"strategy": strategy, "inflation_assumption": inflation}
            paths.append(result.daily.assign(**identity))
            payments.append(result.payments.assign(**identity))
    return {
        "comparison": bundle.tables["portfolio"]["evaluation_metrics"].merge(
            bundle.tables["portfolio"]["performance_ratios"], on="strategy", suffixes=("", "_ratio")
        ),
        "backtest_tests": pd.DataFrame(
            [row for frame in tests for row in frame.to_dict("records")]
        ),
        "backtest_lights": pd.concat(lights, ignore_index=True),
        "spending_summary": pd.DataFrame(summaries),
        "observed_real": pd.DataFrame(observed),
        "spending_paths": pd.concat(paths, ignore_index=True),
        "spending_payments": pd.concat(payments, ignore_index=True),
    }


def build_decision(root: Path, snapshot: Path) -> Path:
    bundle_path = root / "output/app" / snapshot.name / "bundle.json"
    bundle = load_bundle(root, bundle_path)
    output = root / "output/decision" / snapshot.name
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "manifest.json", {"status": "building"})
    try:
        fred_columns = pd.read_csv(snapshot / "fred.csv", nrows=0).columns.tolist()
        if fred_columns != ["observation_date", "DGS3MO"]:
            raise ValueError("Original market snapshot must retain its DGS3MO-only FRED input")
        cpi, cpi_manifest = load_frozen_cpi(root, bundle.metadata["risk"]["as_of"])
        tables = decision_tables(bundle, cpi)
        for name, table in tables.items():
            table.to_csv(output / f"{name}.csv", index=False, float_format="%.17g")
        summary = {
            "snapshot_id": snapshot.name,
            "decision": DECISION,
            "conditional_candidate": "minimum_volatility",
            "approval_status": "proposed_research_only_human_decision_pending",
            "conditions": CONDITIONS,
            "inflation_limitation": CPI_LIMITATION,
            "observed_real_wealth": dict(
                zip(tables["observed_real"].strategy, tables["observed_real"].ending_real_wealth)
            ),
            "observed_real_objective_met": dict(
                zip(
                    tables["observed_real"].strategy,
                    tables["observed_real"].objective_met_in_observed_period,
                )
            ),
            "observed_real_start": tables["observed_real"].start_date.iloc[0],
            "observed_real_end": tables["observed_real"].end_date.iloc[0],
            "cpi_source": {
                "series": cpi_manifest["series"],
                "source_url": cpi_manifest["source_url"],
                "first_observation": cpi_manifest["first_observation"],
                "last_observation": cpi_manifest["last_observation"],
                "latest_observation_release_date": cpi_manifest["latest_observation_release_date"],
                "retrieved_at_utc": cpi_manifest["retrieved_at_utc"],
            },
            "inflation_scenarios": INFLATION_SCENARIOS,
            "withdrawal_rate": WITHDRAWAL_RATE,
            "real_capital_objective": REAL_CAPITAL_OBJECTIVE,
            "payment_rule": "First observed exchange session on/after each funding anniversary; "
            "first payment 3% of initial capital; subsequent payments indexed relative to the "
            "first payment using the assumed deflator. No final partial-year payment.",
            "funding_rule": "After daily returns and any month-end rebalance, sell all holdings "
            "proportionally. Gross sale = net payment / (1 - cost rate). No external cash, "
            "taxes, fixed commissions, minimum lots or market impact. Shortfalls are explicit.",
            "deflator_rule": "Observed-period: CPI at ending month / CPI at starting month; "
            "hypothetical spending: (1 + assumed annual inflation) ** (calendar days / 365.25)",
            "objective_note": "Original 3% real-growth target is before withdrawals and is "
            "measured retrospectively over the CPI-covered period. After-withdrawal 3% "
            "real remaining-capital growth is a separate stricter hypothetical sensitivity. "
            "Neither is a forecast of the full ten-year horizon.",
            "horizon_note": "The observed evaluation is under five years, not evidence of "
            "ten-year spending sustainability. No ten-year extrapolation is made.",
        }
        write_json(output / "summary.json", summary)
        tracked = sorted((root / "src/saifa").rglob("*.py")) + [root / "uv.lock"]
        tracked += [root / "docs/final/01-planning/02-client-investment-policy.md"]
        tracked += [root / "data/inflation/manifest.json", root / "data/inflation/CPIAUCSL.csv"]
        revision, dirty = git_provenance(root)
        write_json(
            output / "manifest.json",
            {
                "schema_version": 1,
                "status": "complete",
                "snapshot_id": snapshot.name,
                "source_bundle_sha256": file_hash(bundle_path),
                "git_head": revision,
                "working_tree_dirty": dirty,
                "source_files": {str(p.relative_to(root)): file_hash(p) for p in tracked},
                "files": {
                    p.name: file_hash(p)
                    for p in [output / "summary.json", *sorted(output.glob("*.csv"))]
                },
            },
        )
        return output
    except Exception as exc:
        write_json(output / "manifest.json", {"status": "failed", "error": str(exc)})
        raise
