"""Build constrained portfolios and compare them out of sample with the 40/60 baseline."""

from dataclasses import asdict
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from saifa.application.data_pipeline import build_data
from saifa.data.snapshots import file_hash, load_snapshot, write_json, write_output_manifest
from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.models.optimisation import efficient_frontier, fit_target_allocations
from saifa.models.performance import performance_ratios
from saifa.models.portfolio import complete_month_ends, performance_metrics, simulate_portfolio


def _read_frame(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, index_col="Date", parse_dates=True, float_precision="round_trip")


def _month_ends(prices: pd.DataFrame, calendar_name: str) -> pd.DatetimeIndex:
    calendar_end = prices.index[-1] + pd.offsets.MonthEnd(1) + pd.Timedelta(days=7)
    sessions = xcals.get_calendar(
        calendar_name, start=prices.index[0], end=calendar_end
    ).sessions.tz_localize(None)
    return complete_month_ends(prices.index, sessions)


def build_optimised_portfolios(
    root: Path, snapshot: Path, config: OptimisationConfig | None = None
) -> Path:
    config = config or OptimisationConfig()
    data_output = build_data(root, snapshot)
    data_config, _, _, _ = load_snapshot(snapshot)
    prices = _read_frame(data_output / "adjusted_prices.csv").loc[:, list(UNIVERSE)]
    simple_returns = _read_frame(data_output / "simple_returns.csv").loc[:, list(UNIVERSE)]
    risk_free = _read_frame(data_output / "risk_free_returns.csv")
    development = simple_returns.loc[simple_returns.index < config.development_end_exclusive]
    validation = simple_returns.loc[
        (simple_returns.index >= config.development_end_exclusive)
        & (simple_returns.index < config.validation_end_exclusive)
    ]
    evaluation_prices = prices.loc[
        (prices.index >= config.validation_end_exclusive)
        & (prices.index < config.evaluation_end_exclusive)
    ]
    if development.empty or validation.empty or len(evaluation_prices) < 2:
        raise ValueError("Configured development, validation or evaluation period is empty")

    fit = fit_target_allocations(simple_returns, risk_free.simple_return, config)
    means, covariance = fit.means, fit.covariance
    annual_risk_free, candidates = fit.annual_risk_free, fit.candidates
    frontier = efficient_frontier(means, covariance, annual_risk_free, config)

    evaluation_month_ends = _month_ends(evaluation_prices, data_config.calendar)
    baseline_weights = pd.Series({"SPY": 0.40, "AGG": 0.60})
    baseline_prices = evaluation_prices.loc[:, baseline_weights.index]
    runs = [
        simulate_portfolio(
            baseline_prices,
            baseline_weights,
            config.initial_capital,
            config.transaction_cost_rate,
            evaluation_month_ends,
            "baseline_40_60",
        )
    ]
    for result in candidates:
        runs.append(
            simulate_portfolio(
                evaluation_prices,
                result.weights,
                config.initial_capital,
                config.transaction_cost_rate,
                evaluation_month_ends,
                result.name,
            )
        )

    baseline_returns = runs[0].daily.daily_return.iloc[1:]
    market_returns = simple_returns.loc[evaluation_prices.index[1:], "SPY"]
    evaluation_risk_free = risk_free.loc[evaluation_prices.index[1:], "simple_return"]
    metric_rows, ratio_rows = [], []
    for run in runs:
        metric_rows.append(
            performance_metrics(run, config.initial_capital, config.annual_trading_days)
        )
        ratio = performance_ratios(
            run.daily.daily_return.iloc[1:],
            market_returns,
            evaluation_risk_free,
            baseline_returns,
            config.annual_trading_days,
        )
        ratio_rows.append({"strategy": run.strategy, **ratio})

    weights_rows = []
    for result in candidates:
        row = {
            "strategy": result.name,
            "development_expected_return": result.expected_return,
            "development_volatility": result.volatility,
            "development_sharpe": result.sharpe,
            "solver_success": result.success,
            "solver_message": result.message,
        }
        row.update({f"weight_{ticker}": result.weights[ticker] for ticker in UNIVERSE})
        weights_rows.append(row)
    weights_frame = pd.DataFrame(weights_rows)
    validation_rows = []
    for result in candidates:
        portfolio = validation @ result.weights
        validation_rows.append(
            {
                "strategy": result.name,
                "observations": len(portfolio),
                "annualised_arithmetic_return": portfolio.mean() * config.annual_trading_days,
                "annualised_volatility": portfolio.std(ddof=1)
                * np.sqrt(config.annual_trading_days),
            }
        )

    output = root / "output" / "optimisation" / snapshot.name
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "status.json", {"snapshot_id": snapshot.name, "status": "building"})
    try:
        weights_frame.to_csv(output / "candidate_weights.csv", index=False, float_format="%.17g")
        frontier.to_csv(output / "efficient_frontier.csv", index=False, float_format="%.17g")
        pd.DataFrame(validation_rows).to_csv(
            output / "validation_metrics.csv", index=False, float_format="%.17g"
        )
        metrics = pd.DataFrame(metric_rows)
        ratios = pd.DataFrame(ratio_rows)
        metrics.to_csv(output / "evaluation_metrics.csv", index=False, float_format="%.17g")
        ratios.to_csv(output / "performance_ratios.csv", index=False, float_format="%.17g")
        pd.concat((run.daily.reset_index() for run in runs), ignore_index=True).to_csv(
            output / "evaluation_daily.csv", index=False, float_format="%.17g"
        )
        pd.concat((run.transactions.reset_index() for run in runs), ignore_index=True).to_csv(
            output / "evaluation_transactions.csv", index=False, float_format="%.17g"
        )

        report = f"""# Constrained portfolio construction report

Snapshot: {snapshot.name}

- Development inputs: {development.index[0].date()} to {development.index[-1].date()}.
- Validation diagnostics: {validation.index[0].date()} to {validation.index[-1].date()}.
- Final evaluation: {evaluation_prices.index[0].date()} to {evaluation_prices.index[-1].date()}.
- Expected returns and covariance are estimated only from development data.
- All evaluation strategies use monthly rebalancing and {config.transaction_cost_bps:.0f} bps on gross buys plus sells.
- SPY is the CAPM market proxy. It is an imperfect proxy for a global mixed-asset endowment.

## Frozen candidate weights

| Strategy | SPY | EFA | EEM | AGG | GLD | XLE | XLK | Development return | Development volatility | Development Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
"""
        for row in weights_rows:
            report += (
                f"| {row['strategy']} | {row['weight_SPY']:.2%} | {row['weight_EFA']:.2%} | "
                f"{row['weight_EEM']:.2%} | {row['weight_AGG']:.2%} | {row['weight_GLD']:.2%} | "
                f"{row['weight_XLE']:.2%} | {row['weight_XLK']:.2%} | "
                f"{row['development_expected_return']:.2%} | {row['development_volatility']:.2%} | "
                f"{row['development_sharpe']:.2f} |\n"
            )
        report += """

## Out-of-sample evaluation

| Strategy | Ending value | Annualised return | Volatility | Maximum drawdown | Sharpe | Sortino | Beta | Treynor | Jensen alpha | Information ratio | Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
"""
        combined = metrics.merge(ratios, on="strategy", suffixes=("", "_ratio"))
        for _, row in combined.iterrows():
            report += (
                f"| {row.strategy} | ${row.ending_value:,.2f} | {row.annualised_return:.2%} | "
                f"{row.annualised_volatility:.2%} | {row.maximum_drawdown:.2%} | "
                f"{row.sharpe_ratio:.2f} | {row.sortino_ratio:.2f} | {row.beta:.2f} | "
                f"{row.treynor_ratio:.2%} | {row.jensen_alpha:.2%} | "
                f"{row.information_ratio:.2f} | {row.calmar_ratio:.2f} |\n"
            )
        report += """

Arithmetic historical means are uncertain forecasts, so neither optimized candidate is automatically a recommendation. Information ratio is measured against the costed 40/60 baseline. CAPM alpha, beta and Treynor use SPY and lagged FRED DGS3MO cash accrual. Ratios are undefined when their denominator is zero; CSV outputs preserve those cases rather than inventing a value. See the manual verification worksheet before human sign-off.
"""
        (output / "optimisation_report.md").write_text(report, encoding="utf-8")
        summary = {
            "snapshot_id": snapshot.name,
            "config": asdict(config),
            "development_observations": len(development),
            "validation_observations": len(validation),
            "evaluation_price_observations": len(evaluation_prices),
            "development_annual_risk_free": annual_risk_free,
            "candidate_solver_status": {result.name: result.message for result in candidates},
            "human_validation": "pending",
            "outputs_sha256": {p.name: file_hash(p) for p in sorted(output.glob("*.csv"))},
        }
        write_json(output / "summary.json", summary)
        write_json(
            output / "status.json",
            {"snapshot_id": snapshot.name, "status": "complete", "human_validation": "pending"},
        )
    except Exception as exc:
        write_json(
            output / "status.json",
            {
                "snapshot_id": snapshot.name,
                "status": "failed",
                "error": f"{type(exc).__name__}: {exc}",
            },
        )
        write_output_manifest(output, snapshot.name)
        raise
    write_output_manifest(output, snapshot.name)
    return output
