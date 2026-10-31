"""Compare annual refitting against frozen allocations, without mutating the base bundle."""

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from saifa.application.optimisation_pipeline import _month_ends
from saifa.dashboard.data import inside, load_bundle
from saifa.data.snapshots import file_hash, write_json
from saifa.domain.adaptive import ADAPTIVE_STRATEGIES, AdaptiveConfig
from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.models.adaptive import annual_execution_dates, fit_annual_targets
from saifa.models.performance import performance_ratios
from saifa.models.portfolio import performance_metrics, simulate_portfolio


def build_adaptive(root: Path, snapshot: Path) -> Path:
    """Requires the verified offline app bundle; no downloads or base-stage regeneration."""
    bundle_path = root / "output/app" / snapshot.name / "bundle.json"
    bundle = load_bundle(root, bundle_path)
    policy = OptimisationConfig(**bundle.metadata["portfolio"]["config"])
    config = AdaptiveConfig(portfolio=policy)
    data_path = inside(root, bundle.manifest["stages"]["data"]["path"])
    source_inputs = {}
    inputs = {}
    for name in ("adjusted_prices", "risk_free_returns"):
        path = data_path / f"{name}.csv"
        digest = file_hash(path)
        if digest != bundle.metadata["data"]["outputs_sha256"][path.name]:
            raise ValueError(f"Data evidence changed: {path.name}")
        source_inputs[str(path.relative_to(root))] = digest
        inputs[name] = pd.read_csv(
            path, index_col="Date", parse_dates=True, float_precision="round_trip"
        )
    prices = inputs["adjusted_prices"].loc[:, list(UNIVERSE)]
    returns = bundle.tables["data"]["simple_returns"].copy()
    returns["Date"] = pd.to_datetime(returns.Date)
    returns = returns.set_index("Date").loc[:, list(UNIVERSE)]
    rates = inputs["risk_free_returns"].simple_return
    weights = (
        bundle.tables["risk"]["portfolio_weights"].set_index("strategy").loc[:, list(UNIVERSE)]
    )
    period_bounds = {
        "validation": (policy.development_end_exclusive, policy.validation_end_exclusive),
        "evaluation": (policy.validation_end_exclusive, policy.evaluation_end_exclusive),
    }
    research_prices = prices.loc[
        (prices.index >= policy.development_end_exclusive)
        & (prices.index < policy.evaluation_end_exclusive)
    ]
    output = root / "output/adaptive" / snapshot.name
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "manifest.json", {"status": "building", "snapshot_id": snapshot.name})
    metrics, daily, transactions = [], [], []
    try:
        targets = fit_annual_targets(
            annual_execution_dates(research_prices.index), returns, rates, config
        )
        for period, (start, end) in period_bounds.items():
            observed = prices.loc[(prices.index >= start) & (prices.index < end)]
            if len(observed) < 2:
                raise ValueError(f"Insufficient {period} prices")
            rebalances = _month_ends(observed, bundle.metadata["data"]["config"]["calendar"])
            runs = []
            for strategy in ADAPTIVE_STRATEGIES:
                schedule = None
                if strategy.startswith("annual_"):
                    rows = targets.loc[
                        (targets.strategy == strategy)
                        & (targets.execution_date >= str(observed.index[0].date()))
                        & (targets.execution_date <= str(observed.index[-1].date()))
                    ]
                    schedule = rows.set_index(pd.to_datetime(rows.execution_date)).loc[
                        :, list(UNIVERSE)
                    ]
                    initial_weights = schedule.iloc[0]
                else:
                    initial_weights = weights.loc[strategy]
                run = simulate_portfolio(
                    observed,
                    initial_weights,
                    policy.initial_capital,
                    policy.transaction_cost_rate,
                    rebalances,
                    strategy,
                    target_schedule=schedule,
                )
                runs.append(run)
            for run in runs:
                result = performance_metrics(
                    run, policy.initial_capital, policy.annual_trading_days
                )
                ratios = performance_ratios(
                    run.daily.daily_return.iloc[1:],
                    returns.loc[observed.index[1:], "SPY"],
                    rates.reindex(observed.index[1:]),
                    runs[0].daily.daily_return.iloc[1:],
                    policy.annual_trading_days,
                )
                metrics.append(
                    {
                        "period": period,
                        **result,
                        "sharpe_ratio": ratios["sharpe_ratio"],
                        "annual_target_updates": int(
                            run.transactions.event.eq("annual_reoptimisation").sum()
                        ),
                    }
                )
                daily.append(run.daily.reset_index().assign(period=period))
                transactions.append(run.transactions.reset_index().assign(period=period))
        metric_frame = pd.DataFrame(metrics)
        changes = []
        for period, rows in metric_frame.groupby("period", sort=False):
            indexed = rows.set_index("strategy")
            for objective in ("minimum_volatility", "maximum_sharpe"):
                frozen, annual = indexed.loc[objective], indexed.loc[f"annual_{objective}"]
                changes.append(
                    {
                        "period": period,
                        "objective": objective,
                        "ending_value_change_usd": annual.ending_value - frozen.ending_value,
                        "annualised_return_change_fraction": annual.annualised_return
                        - frozen.annualised_return,
                        "annualised_volatility_change_fraction": annual.annualised_volatility
                        - frozen.annualised_volatility,
                        "drawdown_loss_change_fraction": -annual.maximum_drawdown
                        + frozen.maximum_drawdown,
                        "trading_cost_change_usd": annual.total_transaction_cost
                        - frozen.total_transaction_cost,
                    }
                )
        tables = {
            "annual_targets": targets,
            "metrics": metric_frame,
            "daily": pd.concat(daily, ignore_index=True),
            "transactions": pd.concat(transactions, ignore_index=True),
            "comparison": pd.DataFrame(changes),
        }
        for name, frame in tables.items():
            frame.to_csv(output / f"{name}.csv", index=False, float_format="%.17g")
        summary = {
            "snapshot_id": snapshot.name,
            "config": asdict(config),
            "design_status": "retrospective research extension; evaluation already viewed",
            "execution_rule": "Fit on the preceding five complete calendar years. Trade at the first session close each year; the previous holdings earn that session's return. Monthly closes then rebalance to the current annual target.",
            "failure_rule": "Missing history, rates or solver failure aborts the experiment; no fallback weights.",
            "scope": "Separate USD 10m starts for validation and evaluation. No withdrawals; adjusted distributions reinvested. Same policy limits and gross-trade costs as frozen candidates.",
            "comparison_limitation": "Annual candidates use trailing-five-year estimates; the original frozen candidates use the full pre-2019 development history. This comparison changes both estimation history and update frequency, so differences cannot be attributed to annual refitting alone.",
            "risk_scope": "Existing VaR, ES, backtests, crisis replays and spending outputs describe frozen candidates only. Adaptive equivalents and final suitability are not established.",
            "human_validation": "pending",
            "source_inputs": source_inputs,
        }
        write_json(output / "summary.json", summary)
        sources = sorted((root / "src/saifa").rglob("*.py")) + [root / "uv.lock"]
        write_json(
            output / "manifest.json",
            {
                "schema_version": 1,
                "status": "complete",
                "snapshot_id": snapshot.name,
                "source_bundle_sha256": file_hash(bundle_path),
                "source_inputs": source_inputs,
                "source_files": {str(p.relative_to(root)): file_hash(p) for p in sources},
                "files": {
                    p.name: file_hash(p)
                    for p in [output / "summary.json", *[output / f"{n}.csv" for n in tables]]
                },
            },
        )
    except Exception as exc:
        write_json(
            output / "manifest.json",
            {
                "status": "failed",
                "snapshot_id": snapshot.name,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise
    return output
