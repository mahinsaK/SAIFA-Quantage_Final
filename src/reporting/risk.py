"""Plain-language risk comparison from computed results."""

import pandas as pd


def _confidence_label(value: float) -> str:
    return f"{100 * value:.10f}".rstrip("0").rstrip(".") + "%"


def render_risk_report(results: pd.DataFrame, context: dict) -> str:
    lines = [
        "# One-day VaR and Expected Shortfall comparison",
        "",
        f"Snapshot: {context['snapshot_id']}",
        f"As of close: {context['as_of']}; forecast session: {context['forecast_session']}.",
        (
            f"Window: {context['window_start']} to {context['as_of']} "
            f"({context['observations']} observed daily returns)."
        ),
        f"Comparison NAV: USD {context['reference_nav']:,.2f} for EACH allocation.",
        "",
        (
            "These are fixed target-weight market-risk scenarios. The baseline is exactly 40% SPY / "
            "60% AGG; the optimized target weights are estimated on development data ending "
            f"{context['weights_estimation_last_date']}. They are not the drifted current holdings "
            "or actual ending wealth from the historical portfolio runs. All methods hold those "
            "same exposures for one trading session, without trading or an added transaction charge."
        ),
        "",
        (
            "Positive numbers mean loss; negative numbers mean a gain threshold and are not "
            "floored at zero. VaR is a loss quantile, not a maximum possible loss. ES averages "
            "the worst (1 - confidence) probability mass, including fractional boundary mass."
        ),
        "",
        "| Portfolio | Method | Confidence | VaR (%) | ES (%) | VaR (USD) | ES (USD) |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for row in results.itertuples():
        lines.append(
            f"| {row.strategy} | {row.method} | {_confidence_label(row.confidence)} | "
            f"{row.var_percent:.4f} | {row.es_percent:.4f} | "
            f"{row.var_usd:,.2f} | {row.es_usd:,.2f} |"
        )
    lines.extend(
        [
            "",
            "## Method comparisons",
            "",
            (
                "Historical simulation retains the observed joint ETF return rows and their tails. "
                "It cannot extrapolate beyond observed scenarios. Parametric Normal uses daily "
                "mean and sample covariance. Monte Carlo draws correlated Normal asset returns "
                "from the SAME moments. Their agreement is expected for linear portfolios; "
                "Monte Carlo is a numerical check, not an independent fat-tail model."
            ),
            "",
            (
                f"Monte Carlo uses {context['simulations']:,} scenarios and PCG64 seed "
                f"{context['seed']}. The same joint scenarios are used for all allocations."
            ),
            "",
            (
                "| Portfolio | Confidence | Historical minus Normal VaR (percentage points) | "
                "MC minus Normal VaR (percentage points) | MC minus Normal ES (percentage points) |"
            ),
            "|---|---:|---:|---:|---:|",
        ]
    )
    for (strategy, confidence), group in results.groupby(["strategy", "confidence"], sort=False):
        methods = group.set_index("method")
        historical = methods.loc["historical"]
        normal = methods.loc["parametric_normal"]
        mc = methods.loc["monte_carlo_normal"]
        lines.append(
            f"| {strategy} | {_confidence_label(confidence)} | "
            f"{historical.var_percent - normal.var_percent:+.4f} | "
            f"{mc.var_percent - normal.var_percent:+.4f} | "
            f"{mc.es_percent - normal.es_percent:+.4f} |"
        )
    lines.extend(
        [
            "",
            "## Limitations and review",
            "",
            (
                "Monte Carlo standard errors in risk_estimates.csv are in decimal-return units "
                "and describe simulation error conditional on fitted parameters only. Increasing "
                "the draw count does not remove uncertainty in the historical sample or the Normal assumption."
            ),
            "",
            (
                "The 1,000-observation default contains only 10 effective observations in the 99% "
                "historical tail. Estimates can be unstable. Window, confidence and sample warnings "
                "are recorded per row. Gaussian simple returns can theoretically fall below -100%; "
                "they are not clipped, and any simulated portfolio occurrences are flagged."
            ),
            "",
            (
                "This is an as-of risk estimate using information through that close, for the next "
                "session. It is not a walk-forward backtest or evidence of calibrated coverage. "
                "No model is selected or tuned on these results. The existing final-period portfolio "
                "performance has already been viewed, so this is not a newly untouched holdout. "
                "ETF adjustments and source histories may be revised. No intraday execution, "
                "withdrawals, liquidity shocks, fees or future rebalancing costs are modelled here."
            ),
            "",
            (
                "Complete docs/final/05-risk-models/03-manual-risk-check.md before recording human validation. "
                "EVT, stress analysis and formal VaR backtesting remain separate milestones."
            ),
            "",
        ]
    )
    for warning in results.warning[results.warning.ne("")].drop_duplicates():
        lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"
