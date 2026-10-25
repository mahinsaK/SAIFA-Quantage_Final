"""Build the transparent 40% SPY / 60% AGG comparator."""

from dataclasses import asdict
from pathlib import Path

import exchange_calendars as xcals
import pandas as pd

from saifa.application.data_pipeline import build_data
from saifa.data.snapshots import file_hash, load_snapshot, write_json, write_output_manifest
from saifa.domain.config import BaselinePortfolioConfig
from saifa.models.portfolio import complete_month_ends, performance_metrics, simulate_portfolio


def build_baseline_portfolio(
    root: Path, snapshot: Path, config: BaselinePortfolioConfig | None = None
) -> Path:
    config = config or BaselinePortfolioConfig()
    data_output = build_data(root, snapshot)
    data_config, _, _, _ = load_snapshot(snapshot)
    prices = pd.read_csv(
        data_output / "adjusted_prices.csv",
        index_col="Date",
        parse_dates=True,
        float_precision="round_trip",
    ).loc[:, list(config.tickers)]
    calendar_end = prices.index[-1] + pd.offsets.MonthEnd(1) + pd.Timedelta(days=7)
    calendar = xcals.get_calendar(
        data_config.calendar, start=prices.index[0], end=calendar_end
    ).sessions.tz_localize(None)
    month_ends = complete_month_ends(prices.index, calendar)
    weights = pd.Series(config.weights, index=config.tickers, dtype=float)
    runs = (
        simulate_portfolio(prices, weights, config.initial_capital, 0, (), "buy_and_hold_no_cost"),
        simulate_portfolio(
            prices,
            weights,
            config.initial_capital,
            0,
            month_ends,
            "monthly_rebalanced_no_cost",
        ),
        simulate_portfolio(
            prices,
            weights,
            config.initial_capital,
            config.transaction_cost_rate,
            month_ends,
            "monthly_rebalanced_10bps",
        ),
    )
    output = root / "output" / "portfolio" / snapshot.name
    output.mkdir(parents=True, exist_ok=True)
    status = {"snapshot_id": snapshot.name, "status": "building"}
    write_json(output / "status.json", status)
    try:
        daily = pd.concat((run.daily.reset_index() for run in runs), ignore_index=True)
        transactions = pd.concat(
            (run.transactions.reset_index() for run in runs), ignore_index=True
        )
        metrics = pd.DataFrame(
            [
                performance_metrics(run, config.initial_capital, config.annual_trading_days)
                for run in runs
            ]
        )
        reporting_dates = month_ends.union(pd.DatetimeIndex([prices.index[0]]))
        weight_columns = [f"{ticker}_weight" for ticker in config.tickers]
        monthly_weights = daily.loc[
            daily.Date.isin(reporting_dates), ["Date", "strategy", *weight_columns]
        ]
        daily.to_csv(output / "portfolio_daily.csv", index=False, float_format="%.17g")
        metrics.to_csv(output / "portfolio_metrics.csv", index=False, float_format="%.17g")
        monthly_weights.to_csv(output / "monthly_weights.csv", index=False, float_format="%.17g")
        transactions.to_csv(output / "transactions.csv", index=False, float_format="%.17g")
        metric_rows = metrics.set_index("strategy")
        cost_row = metric_rows.loc["monthly_rebalanced_10bps"]
        no_cost_row = metric_rows.loc["monthly_rebalanced_no_cost"]
        report = f"""# 40/60 baseline portfolio report

Snapshot: {snapshot.name}

This is a comparator, not an optimised allocation or final recommendation. It invests 40% in SPY and 60% in AGG from USD {config.initial_capital:,.0f}. Monthly strategies trade at the close of each complete calendar month's final XNYS session. The truncated final month is not rebalanced.

| Strategy | Ending value | Cumulative return | Annualised return | Annualised volatility | Maximum drawdown | Total cost |
|---|---:|---:|---:|---:|---:|---:|
"""
        for _, row in metrics.iterrows():
            report += (
                f"| {row.strategy} | ${row.ending_value:,.2f} | {row.cumulative_return:.2%} | "
                f"{row.annualised_return:.2%} | {row.annualised_volatility:.2%} | "
                f"{row.maximum_drawdown:.2%} | ${row.total_transaction_cost:,.2f} |\n"
            )
        report += f"""

The 10 bps strategy charges transaction cost on buys plus sells. Initial funding is also charged: investable NAV is initial capital divided by 1.001, so it never borrows to pay the opening cost. At every rebalance, post-cost NAV x solves `x + 0.001 * sum(abs(target_weight * x - pre_trade_asset_value)) = pre_trade_NAV`. Therefore buys, sells and cost balance exactly.

- Complete scheduled rebalances: {int(cost_row.scheduled_rebalances)}.
- Total 10 bps transaction cost, including initial allocation: ${cost_row.total_transaction_cost:,.2f}.
- Difference from otherwise identical no-cost monthly ending value: ${no_cost_row.ending_value - cost_row.ending_value:,.2f}. This includes direct costs and forgone growth on money paid as costs.
- Daily portfolio return is post-trade NAV divided by the prior post-trade NAV minus one. The first row records initial allocation cost relative to USD 10m.
- Cumulative return and annualised return use initial USD 10m. Volatility excludes the one-time initial allocation cost but includes recurring rebalance costs. Maximum drawdown uses initial USD 10m as the opening high-water mark.
- Adjusted-price returns assume distributions are reinvested. Taxes, market impact, bid-ask variation, management fees and fractional-share constraints are not modelled.
- All three strategies use the same dates and prices. This is full-history descriptive evidence, not out-of-sample proof or an investable recommendation.

See docs/final/03-baseline/01-baseline-methodology.md and docs/final/03-baseline/03-manual-accounting-check.md.
"""
        (output / "baseline_report.md").write_text(report, encoding="utf-8")
        summary = {
            "snapshot_id": snapshot.name,
            "config": asdict(config),
            "first_price": prices.index[0].date().isoformat(),
            "last_price": prices.index[-1].date().isoformat(),
            "complete_month_ends": len(month_ends),
            "human_validation": "pending",
            "outputs_sha256": {p.name: file_hash(p) for p in sorted(output.glob("*.csv"))},
        }
        write_json(output / "summary.json", summary)
        status.update(status="complete", human_validation="pending")
    except Exception as exc:
        status.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        write_json(output / "status.json", status)
        write_output_manifest(output, snapshot.name)
        raise
    write_json(output / "status.json", status)
    write_output_manifest(output, snapshot.name)
    return output
