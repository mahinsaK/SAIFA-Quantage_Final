"""Offline, separately published research lab using the verified frozen bundle."""

from dataclasses import asdict
from pathlib import Path

import pandas as pd

from saifa.application.optimisation_pipeline import _month_ends
from saifa.dashboard.data import inside, load_bundle
from saifa.dashboard.selections import backtest_view
from saifa.data.inflation import load_frozen_cpi
from saifa.data.snapshots import file_hash, load_snapshot, write_json
from saifa.domain.config import UNIVERSE, BacktestConfig, OptimisationConfig
from saifa.domain.dashboard import CONFIDENCES, STRATEGIES
from saifa.domain.research import RESEARCH_TABLES, VOLATILITY_METHODS, ResearchConfig
from saifa.models.optimisation import annualised_inputs
from saifa.models.portfolio import performance_metrics, simulate_portfolio
from saifa.models.research.allocations import (
    constrained_risk_parity,
    minimum_es,
    variance_risk_shares,
)
from saifa.models.research.implementation import cost_metrics, income_proxy, liquidity_proxy
from saifa.models.research.robustness import allocation_robustness
from saifa.models.research.sustainability import joint_monthly_inputs, spending_experiment
from saifa.models.research.volatility import volatility_experiment
from saifa.models.risk import empirical_tail


def publish_research(
    root: Path,
    snapshot_id: str,
    bundle_path: Path,
    tables: dict[str, pd.DataFrame],
    summary: dict,
    source_inputs: dict[str, str],
) -> Path:
    if set(tables) != set(RESEARCH_TABLES):
        raise ValueError("Incomplete research output tables")
    folder = root / "output/research" / snapshot_id
    folder.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(folder / f"{name}.csv", index=False, float_format="%.17g")
    write_json(folder / "summary.json", summary)
    sources = sorted((root / "src/saifa").rglob("*.py")) + [root / "uv.lock"]
    write_json(
        folder / "manifest.json",
        {
            "schema_version": 1,
            "status": "complete",
            "snapshot_id": snapshot_id,
            "source_bundle_sha256": file_hash(bundle_path),
            "source_inputs": source_inputs,
            "source_files": {str(p.relative_to(root)): file_hash(p) for p in sources},
            "files": {
                name: file_hash(folder / name)
                for name in ["summary.json", *[f"{n}.csv" for n in RESEARCH_TABLES]]
            },
        },
    )
    return folder


def build_research(
    root: Path, snapshot: Path, settings: ResearchConfig | None = None, progress=print
) -> Path:
    settings = settings or ResearchConfig()
    path = root / "output/app" / snapshot.name / "bundle.json"
    bundle = load_bundle(root, path)
    policy = OptimisationConfig(**bundle.metadata["portfolio"]["config"])
    data_path = inside(root, bundle.manifest["stages"]["data"]["path"])
    inputs, source_inputs = {}, {}
    for name in ("adjusted_prices", "risk_free_returns"):
        p = data_path / f"{name}.csv"
        digest = file_hash(p)
        if digest != bundle.metadata["data"]["outputs_sha256"][p.name]:
            raise ValueError(f"Data source changed: {p.name}")
        inputs[name] = pd.read_csv(
            p, index_col="Date", parse_dates=True, float_precision="round_trip"
        )
        source_inputs[str(p.relative_to(root))] = digest
    prices = inputs["adjusted_prices"].loc[:, list(UNIVERSE)]
    rates = inputs["risk_free_returns"].simple_return
    returns = bundle.tables["data"]["simple_returns"].set_index("Date").loc[:, list(UNIVERSE)]
    returns.index = pd.to_datetime(returns.index)
    config, _, raw, _ = load_snapshot(snapshot)
    cpi, _ = load_frozen_cpi(root, bundle.metadata["risk"]["as_of"])
    for name in ("CPIAUCSL.csv", "manifest.json"):
        p = root / "data/inflation" / name
        source_inputs[str(p.relative_to(root))] = file_hash(p)
    folder = root / "output/research" / snapshot.name
    folder.mkdir(parents=True, exist_ok=True)
    write_json(folder / "manifest.json", {"status": "building", "snapshot_id": snapshot.name})
    try:
        progress("Research: fitting development-only minimum ES and constrained risk parity...")
        development = returns.loc[returns.index < policy.development_end_exclusive]
        _, covariance = annualised_inputs(development, policy.annual_trading_days)
        frozen = (
            bundle.tables["risk"]["portfolio_weights"]
            .set_index("strategy")
            .loc[list(STRATEGIES), list(UNIVERSE)]
        )
        weights = frozen.copy()
        es_weights, es_details = minimum_es(development, policy, settings.es_confidence)
        rp_weights, rp_details = constrained_risk_parity(covariance, policy)
        weights.loc["minimum_es"] = es_weights
        weights.loc["risk_parity"] = rp_weights
        diagnostics, weight_records = [], []
        for strategy, w in weights.iterrows():
            tail = empirical_tail(-development.to_numpy() @ w.to_numpy(), settings.es_confidence)
            details = (
                es_details
                if strategy == "minimum_es"
                else rp_details
                if strategy == "risk_parity"
                else {"message": "Original verified frozen candidate"}
            )
            diagnostics.append(
                {
                    "strategy": strategy,
                    "development_es_fraction": tail.es_fraction,
                    "training_start": str(development.index[0].date()),
                    "training_end": str(development.index[-1].date()),
                    **details,
                }
            )
            shares = variance_risk_shares(w.to_numpy(), covariance.to_numpy())
            weight_records.append(
                {
                    "strategy": strategy,
                    **w.to_dict(),
                    **{f"risk_share_{t}": v for t, v in zip(UNIVERSE, shares)},
                }
            )
        metrics, daily, transactions, costs, liquidity = [], [], [], [], []
        bounds = {
            "validation": (policy.development_end_exclusive, policy.validation_end_exclusive),
            "evaluation": (policy.validation_end_exclusive, policy.evaluation_end_exclusive),
        }
        progress("Research: same-period candidate comparisons and cost/fee sensitivity...")
        for period, (start, end) in bounds.items():
            observed = prices.loc[(prices.index >= start) & (prices.index < end)]
            rebalances = _month_ends(observed, config.calendar)
            for strategy, w in weights.iterrows():
                for bps in (0.0, 10.0, 25.0):
                    run = simulate_portfolio(
                        observed, w, policy.initial_capital, bps / 10000, rebalances, strategy
                    )
                    for fee in (0.0, 25.0, 50.0):
                        costs.append(
                            {
                                "period": period,
                                "trade_cost_bps": bps,
                                **cost_metrics(
                                    run, policy.initial_capital, policy.annual_trading_days, fee
                                ),
                            }
                        )
                run = simulate_portfolio(
                    observed,
                    w,
                    policy.initial_capital,
                    policy.transaction_cost_rate,
                    rebalances,
                    strategy,
                )
                metrics.append(
                    {
                        "period": period,
                        **performance_metrics(
                            run, policy.initial_capital, policy.annual_trading_days
                        ),
                    }
                )
                daily.append(run.daily.reset_index().assign(period=period))
                transactions.append(run.transactions.reset_index().assign(period=period))
                liquidity.append(liquidity_proxy(run.transactions, raw).assign(period=period))
        progress("Research: development input/window/block-resampling robustness...")
        robustness = allocation_robustness(returns, rates, frozen, policy, settings)
        progress("Research: annual GARCH fits, past-only daily forecasts and EWMA dependence...")
        forecasts, fits, correlations = volatility_experiment(returns, frozen, policy, settings)
        backtest_config = BacktestConfig(
            start=policy.development_end_exclusive,
            end_exclusive=policy.evaluation_end_exclusive,
            confidence_levels=CONFIDENCES,
            reference_nav=policy.initial_capital,
        )
        tests = []
        for strategy in STRATEGIES:
            for method in VOLATILITY_METHODS:
                for confidence in CONFIDENCES:
                    view = backtest_view(
                        forecasts,
                        strategy,
                        method,
                        confidence,
                        forecasts.forecast_date.min(),
                        forecasts.forecast_date.max(),
                        backtest_config,
                        policy.validation_end_exclusive,
                    )
                    tests.append(
                        view.tests.assign(strategy=strategy, method=method, confidence=confidence)
                    )
        progress("Research: joint return/CPI block-resampling spending scenarios...")
        month_ends = _month_ends(prices, config.calendar)
        joint = joint_monthly_inputs(prices.loc[month_ends], cpi)
        spending, fan = spending_experiment(joint, frozen, policy, settings)
        evaluation_prices = prices.loc[
            (prices.index >= policy.validation_end_exclusive)
            & (prices.index < policy.evaluation_end_exclusive)
        ]
        income, income_ledger = income_proxy(
            raw,
            weights,
            str(evaluation_prices.index[0].date()),
            str(evaluation_prices.index[-1].date()),
            policy.initial_capital,
        )
        availability = pd.DataFrame(
            [
                {
                    "Topic": "Rolling re-optimisation",
                    "Status": "Implemented in Portfolio",
                    "Scope": "Portfolio → Annual strategy shows past-only yearly weight refits and costed validation/evaluation comparisons. It remains separate from these six lab topics.",
                },
                {
                    "Topic": "Alternative allocations",
                    "Status": "Implemented research",
                    "Scope": "Development-only minimum empirical ES and policy-constrained risk-share balancing; no prospective risk approval.",
                },
                {
                    "Topic": "Allocation robustness",
                    "Status": "Implemented research",
                    "Scope": "Training windows, mean shocks, fixed diagonal shrinkage and geometric-block resamples; not calibrated confidence intervals.",
                },
                {
                    "Topic": "Volatility / dependence",
                    "Status": "Implemented with limits",
                    "Scope": "GARCH Normal/FHS and EWMA covariance with dated backtests. High/low regimes are descriptive; no fitted Markov regime, DCC or copula model.",
                },
                {
                    "Topic": "Long-horizon spending",
                    "Status": "Conditional simulation",
                    "Scope": "Ten-year resampling of the short recent joint return/CPI sample, spending and inflation-spread sensitivity. Not a calibrated university survival probability.",
                },
                {
                    "Topic": "Separate income",
                    "Status": "Ex-date proxy only",
                    "Scope": "Constant-notional distribution evidence; split-exposed candidates withheld pending unit review. Actual payment dates and taxes missing.",
                },
                {
                    "Topic": "Implementation costs",
                    "Status": "Sensitivity / volume proxy",
                    "Scope": "Assumed gross-trade costs, extra admin fees and prior-volume participation. Actual bid-ask, impact, tax and execution constraints unavailable.",
                },
            ]
        )
        summary = {
            "snapshot_id": snapshot.name,
            "config": asdict(settings),
            "portfolio_config": asdict(policy),
            "design_status": "Retrospective research: validation/evaluation were viewed before extension design. No automatic winner or policy approval.",
            "spending_source_start": str(joint.index[0]),
            "spending_source_end": str(joint.index[-1]),
            "spending_source_months": len(joint),
            "spending_limit": "Joint return/inflation blocks use only the short CPI-overlap period, exclude missing consecutive CPI ratios, and restart at calendar gaps. The sample excludes earlier crises. Conditional simulation frequencies and Wilson intervals cover Monte Carlo sampling only, not model/parameter uncertainty or future probabilities.",
            "income_limit": "Ex-date constant-notional proxy, not actual fund cash; never add distributions to adjusted-price total returns. Payment dates, withholding and split-unit review remain unavailable.",
            "cost_limit": "Trade/admin rates are assumptions. Additional admin fees exclude ETF expenses already embedded in prices. Prior daily dollar volume is not a spread or market-impact estimate.",
            "human_validation": "pending",
            "source_inputs": source_inputs,
            "backtest_config": asdict(backtest_config),
            "sources": [
                "https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf",
                "https://www.thierry-roncalli.com/download/erc.pdf",
                "https://bashtage.github.io/arch/univariate/forecasting.html",
                "https://statistics.stanford.edu/technical-reports/stationary-bootstrap",
                "https://ranaroussi.github.io/yfinance/advanced/price_repair.html",
            ],
        }
        tables = {
            "allocation_weights": pd.DataFrame(weight_records),
            "allocation_diagnostics": pd.DataFrame(diagnostics),
            "candidate_metrics": pd.DataFrame(metrics),
            "candidate_daily": pd.concat(daily, ignore_index=True),
            "candidate_transactions": pd.concat(transactions, ignore_index=True),
            "robustness_weights": robustness,
            "volatility_forecasts": forecasts,
            "volatility_fits": fits,
            "volatility_tests": pd.concat(tests, ignore_index=True),
            "correlations": correlations,
            "spending_summary": spending,
            "spending_fan": fan,
            "spending_inputs": joint.reset_index().assign(month=lambda f: f.month.astype(str)),
            "cost_metrics": pd.DataFrame(costs),
            "liquidity": pd.concat(liquidity, ignore_index=True),
            "income_summary": income,
            "income_ledger": income_ledger,
            "availability": availability,
        }
        return publish_research(root, snapshot.name, path, tables, summary, source_inputs)
    except Exception as exc:
        write_json(
            folder / "manifest.json",
            {
                "status": "failed",
                "snapshot_id": snapshot.name,
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        raise
