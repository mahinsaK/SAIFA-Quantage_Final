"""Diagnostic charts and plain-language EVT report, separate from estimation."""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def plot_diagnostics(
    diagnostics: pd.DataFrame,
    sensitivity: pd.DataFrame,
    qq: pd.DataFrame,
    output: Path,
    selected: float,
) -> None:
    for (strategy, period), group in diagnostics.groupby(["strategy", "period"], sort=False):
        fig, axes = plt.subplots(2, 3, figsize=(14, 8), layout="constrained")
        for ax, y, title in zip(
            axes.flat[:4],
            ["mean_excess", "shape", "modified_scale", "exceedances"],
            [
                "Mean excess (decimal loss)",
                "GPD shape xi",
                "Modified scale: beta - xi*u",
                "Strict exceedances",
            ],
        ):
            # Mean-excess linearity is assessed against the loss threshold u, not its percentile.
            x = "quantile" if y == "exceedances" else "threshold"
            selected_x = group.loc[group["quantile"].eq(selected), x].iloc[0]
            ax.plot(100 * group[x], group[y], "o-")
            ax.axvline(100 * selected_x, color="grey", linestyle="--")
            ax.set(
                xlabel="Threshold percentile" if x == "quantile" else "Loss threshold (%)",
                title=title,
            )
            ax.grid(alpha=0.25)
        tail = sensitivity.loc[sensitivity.strategy.eq(strategy) & sensitivity.period.eq(period)]
        for confidence, rows in tail.groupby("confidence"):
            axes[1, 1].plot(
                100 * rows["quantile"], 100 * rows.var_fraction, "o-", label=f"VaR {confidence:.1%}"
            )
            axes[1, 1].plot(
                100 * rows["quantile"], 100 * rows.es_fraction, "x--", label=f"ES {confidence:.1%}"
            )
        axes[1, 1].set(xlabel="Threshold percentile", ylabel="Loss (%)", title="Tail sensitivity")
        axes[1, 1].legend(fontsize=8)
        points = qq.loc[qq.strategy.eq(strategy) & qq.period.eq(period)]
        if not points.empty:
            axes[1, 2].scatter(points.fitted_excess, points.observed_excess, s=10)
            upper = np.max(points[["fitted_excess", "observed_excess"]].to_numpy())
            axes[1, 2].plot([0, upper], [0, upper], color="grey")
        else:
            axes[1, 2].text(0.1, 0.5, "Selected fit unavailable", transform=axes[1, 2].transAxes)
        axes[1, 2].set(
            xlabel="Fitted GPD excess", ylabel="Observed excess", title="Selected-threshold Q-Q"
        )
        fig.suptitle(f"{strategy} — {period}\nDiagnostic evidence; no automatic threshold approval")
        fig.savefig(output / f"diagnostics_{strategy}_{period}.png", dpi=130)
        plt.close(fig)


def render_evt_report(estimates: pd.DataFrame, diagnostics: pd.DataFrame, context: dict) -> str:
    def number(value, multiplier=1):
        return "unavailable" if pd.isna(value) else f"{value * multiplier:,.4f}"

    lines = [
        "# EVT peaks-over-threshold study",
        "",
        (
            f"Snapshot: {context['snapshot_id']}; close: {context['as_of']}; "
            f"forecast session: {context['forecast_session']}."
        ),
        (
            f"Window: {context['window_start']} to {context['as_of']} "
            f"({context['observations']} returns). Each fixed target allocation: "
            f"USD {context['reference_nav']:,.0f}; one session; positive means loss."
        ),
        "",
        "## Threshold rationale and review",
        "",
        (
            f"The prespecified threshold rule is the {context['threshold_quantile']:.1%} "
            "empirical loss quantile. At the default 1,000 observations, 90% yields about 100 "
            "exceedances: more fitting information than 95% (50), while staying below the "
            "95% and 99% forecast confidence levels. This is a bias/variance research choice, "
            "not a statistically proven optimal threshold. Ties change the actual exceedance count."
        ),
        (
            f"Development diagnostics use {context['development_start']} through "
            f"{context['development_end']}. Only these diagnostics may support changing the rule; "
            "as-of diagnostics are a sensitivity report and do not select it. Prior evaluation "
            "results have already been viewed, so no newly untouched holdout is claimed."
        ),
        (
            "Inspect mean excess, shape/modified-scale stability and Q-Q plots together. "
            "A low threshold may include the distribution body; a high threshold has too few "
            "observations. See docs/final/06-evt/03-manual-evt-check.md for the named review record; "
            "this generated report does not assert human approval. Chart generation and "
            "successful numerical fits alone do not establish adequacy."
        ),
        "",
        "## Estimates and 95% bootstrap intervals",
        "",
        "| Portfolio | Confidence | VaR % | ES % | VaR USD | ES USD | Status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in estimates.itertuples():
        lines.append(
            f"| {row.strategy} | {row.confidence:.1%} | {number(row.var_percent)} | "
            f"{number(row.es_percent)} | {number(row.var_usd)} | {number(row.es_usd)} | {row.status} |"
        )
    lines += [
        "",
        "| Portfolio | Confidence | VaR 95% interval (%) | ES 95% interval (%) | Valid VaR / ES draws |",
        "|---|---:|---|---|---|",
    ]
    for row in estimates.itertuples():
        lines.append(
            f"| {row.strategy} | {row.confidence:.1%} | "
            f"{number(row.var_ci_low, 100)} to {number(row.var_ci_high, 100)} | "
            f"{number(row.es_ci_low, 100)} to {number(row.es_ci_high, 100)} | "
            f"{row.var_valid_replicates} / {row.es_valid_replicates} of {row.bootstrap_replicates} |"
        )
    lines += [
        "",
        "## Threshold diagnostics",
        "",
        "| Portfolio / period | Threshold percentile | Loss threshold % | Count | Shape | Scale | Fit status |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in diagnostics.itertuples():
        lines.append(
            f"| {row.strategy} / {row.period} | {row.quantile:.1%} | "
            f"{number(row.threshold, 100)} | {row.exceedances} | "
            f"{number(row.shape)} | {number(row.scale)} | {row.status} |"
        )
    for strategy in estimates.strategy.unique():
        for period in ("development", "as_of"):
            lines += ["", f"![{strategy} {period}](diagnostics_{strategy}_{period}.png)"]
    lines += [
        "",
        "## Uncertainty and limitations",
        "",
        (
            f"Circular block bootstrap: {context['bootstrap_replicates']} draws, "
            f"{context['block_length']}-session blocks, PCG64 seed {context['seed']}. "
            "Each resample refits the quantile threshold and GPD; the threshold rule and "
            "portfolio weights stay fixed. Intervals describe estimation variability under this "
            "resampling scheme, not a future-loss range or uncertainty in model/portfolio selection."
        ),
        (
            "Blocks preserve some local dependence but neither prove stationarity nor solve "
            "volatility clustering. Block length is a research assumption. The model is unconditional; "
            "no GARCH filtering or declustering is performed. Tail extrapolation can be unreliable."
        ),
        (
            "Confidence at/below the empirical threshold CDF is unsupported; 90% confidence "
            "usually cannot use the default 90% threshold. Do not extrapolate backwards or substitute "
            "a different method under the EVT label. Shape >= 1 has no finite ES. Nonregular MLE "
            "fits (shape <= -0.5), too few exceedances and failed fits are explicitly withheld."
        ),
        (
            "Blank CSV fields mean unavailable, not zero. Inspect status and warning columns. "
            "ES intervals are withheld when valid VaR bootstrap fits include an infinite ES; "
            "this avoids reporting intervals based only on the convenient finite draws."
        ),
        (
            "No trading fees, withdrawals or changing holdings are added to one-session scenarios. "
            "See risk_comparison.csv for all four methods on identical inputs. Coverage tests and "
            "stress validation remain future milestones."
        ),
        "",
    ]
    for column in ("warning", "interval_warning"):
        for warning in estimates[column].dropna().unique():
            if warning:
                lines.append(f"- {warning}")
    return "\n".join(lines) + "\n"
