"""Separate statistical outcomes from narrative and loss/forecast charts."""

from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_backtests(forecasts: pd.DataFrame, output: Path) -> None:
    for (period, strategy), frame in forecasts.groupby(["period", "strategy"], sort=False):
        methods = list(frame.method.unique())
        confidences = sorted(frame.confidence.unique())
        fig, axes = plt.subplots(
            len(methods), len(confidences), figsize=(14, 11), squeeze=False, layout="constrained"
        )
        for i, method in enumerate(methods):
            for j, confidence in enumerate(confidences):
                rows = frame.loc[frame.method.eq(method) & frame.confidence.eq(confidence)]
                dates = pd.to_datetime(rows.forecast_date)
                ax = axes[i, j]
                ax.plot(
                    dates,
                    rows.loss_percent,
                    color="grey",
                    alpha=0.6,
                    linewidth=0.6,
                    label="Realized loss",
                )
                ax.plot(
                    dates, rows.var_percent, color="#2263ad", linewidth=1, label="Prior-close VaR"
                )
                hits = rows.exception.eq(1)
                ax.scatter(
                    dates[hits],
                    rows.loc[hits, "loss_percent"],
                    color="#c33f37",
                    s=12,
                    label="Exception",
                )
                ax.set(title=f"{method} / {confidence:.1%}", ylabel="One-session loss (%)")
                ax.grid(alpha=0.2)
                if i == 0 and j == 0:
                    ax.legend(fontsize=7)
        fig.suptitle(
            f"{strategy} — {period}\nFixed target exposures; forecast precedes realized return"
        )
        fig.savefig(output / f"backtest_{strategy}_{period}.png", dpi=130)
        plt.close(fig)


def render_backtest_report(summary: pd.DataFrame, lights: pd.DataFrame, context: dict) -> str:
    def value(x):
        return "unavailable" if pd.isna(x) else f"{x:.4g}"

    lines = [
        "# Walk-forward VaR validation",
        "",
        f"Snapshot: {context['snapshot_id']}; forecasts: {context['start']} through {context['end']}.",
        (
            f"{context['forecast_sessions']} target sessions; {context['rows']} forecast rows. "
            f"Each window uses {context['lookback']} returns ending at the previous exchange close."
        ),
        (
            f"Weights estimated through {context['weights_as_of']}, then fixed. Each portfolio has "
            f"USD {context['reference_nav']:,.0f} reference NAV, one-session horizon and signed loss = -return."
        ),
        "",
        "## Scope and timing",
        "",
        (
            "This evaluates hypothetical one-day losses of fixed target exposures. It does not backtest "
            "the realized NAV of the monthly-rebalanced strategy or include fees, withdrawals or compounding. "
            "All methods forecast the same dated return and exposures."
        ),
        (
            f"Validation forecasts precede {context['validation_end_exclusive']}; evaluation forecasts "
            "start at that boundary. Results are separate. Earlier portfolio evaluation results were already "
            "viewed; this is retrospective evaluation, not a newly untouched holdout. No method/window/threshold "
            "is chosen or retuned automatically based on these results."
        ),
        (
            f"EVT retains the provisionally reviewed {context['threshold']:.0%} quantile rule, with the "
            "numeric loss threshold refitted from each past-only window. Unsupported or failed forecasts "
            "stay in the table with missing exceptions. Inferential tests are withheld for incomplete sequences."
        ),
        "",
        "## Coverage and independence",
        "",
        (
            f"Decisions use significance {context['significance']:.0%}. 'Do not reject' is not a pass or "
            "proof of correctness. Kupiec's chi-square p-value and an exact two-sided binomial p-value "
            "are both saved; the latter also assumes independent exceptions. No multiple-test correction is applied."
        ),
        (
            f"Christoffersen uses consecutive-session transitions and needs at least "
            f"{context['minimum_previous_state']} transitions from each previous state. Missing/insufficient "
            "transitions are unavailable. Small expected cells make asymptotic p-values uncertain."
        ),
    ]
    for period, rows in summary.groupby("period", sort=False):
        lines += [
            "",
            f"### {period}",
            "",
            "| Portfolio | Method | Confidence | Valid / scheduled | Exceptions / expected | Kupiec p | Exact binomial p | Independence p | Decisions (coverage / independence) |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
        ]
        for r in rows.itertuples():
            lines.append(
                f"| {r.strategy} | {r.method} | {r.confidence:.1%} | "
                f"{r.coverage_valid_forecasts}/{r.coverage_observations} | "
                f"{r.coverage_exceptions}/{r.coverage_expected_exceptions:.2f} | "
                f"{value(r.coverage_p_value)} | {value(r.coverage_exact_p_value)} | "
                f"{value(r.independence_p_value)} | {r.coverage_decision} / {r.independence_decision} |"
            )
    lines += [
        "",
        "## Latest 250-session Basel diagnostic in each period",
        "",
        (
            "At 99% confidence: green = 0–4 exceptions; yellow = 5–9; red = 10 or more. "
            "A 250-session window must have every forecast available. No window crosses the "
            "validation/evaluation boundary, and no adaptation is silently applied to 95% confidence."
        ),
        (
            "This is the historical Basel traffic-light convention used as a research diagnostic. "
            "It is not a claim that this endowment model satisfies bank capital rules."
        ),
        "",
        "| Period | Portfolio | Method | Window | Exceptions | Zone | Status |",
        "|---|---|---|---|---:|---|---|",
    ]
    for r in lights.itertuples():
        lines.append(
            f"| {r.period} | {r.strategy} | {r.method} | {r.start} to {r.end} | "
            f"{value(r.exceptions)} | {r.zone or 'unavailable'} | {r.status} |"
        )
    if lights.empty:
        lines.append("No 99% confidence requested; no canonical Basel view is available.")
    lines += [
        "",
        "## Monte Carlo implementation",
        "",
        (
            f"{context['simulations']:,} standard Normal draws per forecast date, PCG64 base seed "
            f"{context['seed']} combined with the target-date ordinal. The same standardized draw "
            "sample is transformed for each portfolio using its rolling mean and volatility. "
            "This is an exact distributional projection of a linear Gaussian portfolio: portfolio "
            "variance includes asset covariance. It avoids simulating seven ETF columns at every date."
        ),
        (
            "This numeric coupling across portfolios is not a simulated joint portfolio distribution. "
            "Date-specific draws make results independent of the selected start date. Monte Carlo and "
            "Parametric Normal are expected to agree within simulation error; they are not independent "
            "distributional models. Daily draws differ from the original single-as-of simulation realization."
        ),
        "",
        "## Interpretation and review",
        "",
        (
            "Inspect coverage frequency and clustering together. A low exception count alone does not "
            "establish usefulness: an overly conservative model can misstate risk too. Sparse-event tests "
            "have limited power. Rejections should prompt investigation, not removal of crisis dates or "
            "retuning on the evaluation results. These VaR tests do not validate ES severity forecasts."
        ),
        (
            "Review forecasts.csv (including missing statuses), test_summary.csv (transition counts "
            "and warnings), and basel_rolling.csv (all dated windows). Complete "
            "docs/final/manual-backtest-check.md before recording human validation."
        ),
    ]
    for period, rows in summary.groupby("period", sort=False):
        for strategy in rows.strategy.unique():
            lines += ["", f"![{strategy} {period}](backtest_{strategy}_{period}.png)"]
    lines += [
        "",
        (
            "Sources: [Christoffersen (1998)](https://users.ssc.wisc.edu/~behansen/718/Christoffersen1998.pdf), "
            "[Kupiec (1995)](https://fedinprint.org/item/fedgfe/34596/original), "
            "[Basel historical guidance, MAR99](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/99/inforce/2019-12-15/published/2019-12-15)."
        ),
    ]
    return "\n".join(lines) + "\n"
