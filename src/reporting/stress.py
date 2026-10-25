"""Human-readable attribution and scenario results, with explicit scope and units."""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


def plot_stress(frames: dict[str, pd.DataFrame], output: Path) -> list[str]:
    charts = []
    assets = frames["asset_contributions"]
    confidence = float(assets.confidence.max())
    selected = assets.loc[(assets.measure == "es") & (assets.confidence == confidence)]
    strategies = list(selected.strategy.unique())
    fig, axes = plt.subplots(
        1, len(strategies), figsize=(15, 5), squeeze=False, sharey=True, layout="constrained"
    )
    for ax, strategy in zip(axes[0], strategies):
        table = selected.loc[selected.strategy == strategy].pivot(
            index="ticker", columns="method", values="component_usd"
        )
        table = table.reindex(assets.ticker.drop_duplicates()) / 1000
        x = np.arange(len(table))
        for i, method in enumerate(table.columns):
            ax.bar(x + (i - 0.5) * 0.35, table[method], width=0.35, label=method)
        ax.set(
            xticks=x, xticklabels=table.index, title=strategy, ylabel="ES component (USD thousands)"
        )
        ax.axhline(0, color="black", linewidth=0.5)
        ax.tick_params(axis="x", rotation=45)
        ax.legend(fontsize=7)
    fig.suptitle(f"One-session {confidence:.1%} ES contributions; negative values offset risk")
    fig.savefig(output / "es_contributions.png", dpi=130)
    plt.close(fig)
    charts.append("es_contributions.png")
    for number, (scenario, rows) in enumerate(
        frames["historical_paths"].groupby("scenario", sort=False), 1
    ):
        fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, layout="constrained")
        for strategy, path in rows.groupby("strategy", sort=False):
            dates = pd.to_datetime(path.Date)
            axes[0].plot(dates, path.nav / 1e6, label=strategy)
            axes[1].plot(dates, path.drawdown_fraction * 100, label=strategy)
        axes[0].set(
            ylabel="NAV (USD millions)",
            title=f"{scenario}: fixed initial allocation, buy-and-hold replay",
        )
        axes[1].set(ylabel="Drawdown loss (%)")
        locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
        axes[1].xaxis.set_major_locator(locator)
        axes[1].xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
        for ax in axes:
            ax.grid(alpha=0.2)
        axes[0].legend(fontsize=8)
        filename = f"historical_replay_{number:02d}.png"
        fig.savefig(output / filename, dpi=130)
        plt.close(fig)
        charts.append(filename)
    table = (
        frames["hypothetical_summary"].pivot(
            index="strategy", columns="multiplier", values="loss_usd"
        )
        / 1e6
    )
    ax = table.plot.bar(figsize=(10, 5), ylabel="One-session scenario loss (USD millions)", rot=0)
    ax.set_title("Hypothetical joint shock: severity multipliers, no probability assigned")
    ax.legend(title="Shock multiplier")
    ax.figure.tight_layout()
    ax.figure.savefig(output / "hypothetical_loss.png", dpi=130)
    plt.close(ax.figure)
    charts.append("hypothetical_loss.png")
    return charts


def render_stress_report(frames: dict[str, pd.DataFrame], context: dict, charts: list[str]) -> str:
    def number(value, percent=False):
        return (
            "unavailable"
            if pd.isna(value)
            else f"{100 * value:.3f}%"
            if percent
            else f"{value:,.2f}"
        )

    lines = [
        "# Risk contributions and stress analysis",
        "",
        f"Snapshot: {context['snapshot_id']}; settings: {context['run_id']}; as-of close: {context['as_of']}.",
        f"Attribution uses {context['observations']} daily returns from {context['window_start']}, fixed target weights estimated through {context['weights_as_of']}, and USD {context['reference_nav']:,.0f} reference NAV.",
        f"The one-session risk horizon is the next exchange session, {context['forecast_session']}. Proposed review levels: 99% one-day ES {context['es_review_level']:.1%}, crisis drawdown {context['drawdown_review_level']:.1%}, hypothetical loss {context['shock_review_level']:.1%}.",
        "",
        "## One-session risk attribution",
        "",
        "Normal VaR/ES use Euler exposure derivatives, including the mean-return term. Historical ES allocates the same portfolio-tail probability mass to each asset, sharing boundary ties equally. Components sum to portfolio risk when defined; zero holdings have zero components. Negative components and shares above 100% can occur. At zero/near-zero total risk, percentage shares are unavailable. At a zero-volatility hedge, a Normal gradient can be unavailable even though total risk is finite.",
        "A marginal is per unit exposure, without forcing weights to sum to one. For a funded transfer, subtract the donor marginal from the receiver marginal. Historical ES ties can give nonunique subgradients. Empirical VaR, Monte Carlo and EVT attribution are not claimed by this module.",
        "",
        "| Portfolio | Method | Measure | Confidence | Total USD | Sum of components USD | Status | 99% ES review breach |",
        "|---|---|---|---:|---:|---:|---|---|",
    ]
    for r in frames["contribution_summary"].itertuples():
        lines.append(
            f"| {r.strategy} | {r.method} | {r.measure.upper()} | {r.confidence:.1%} | {number(r.total_usd)} | {number(r.component_sum_fraction * context['reference_nav'] if pd.notna(r.component_sum_fraction) else None)} | {r.status} | {r.es_review_trigger_breached if pd.notna(r.es_review_trigger_breached) else 'not applicable'} |"
        )
    lines += [
        "",
        "## Allocation sensitivity",
        "",
        f"sizing_checks.csv reprices all directed {context['transfer_weight'] * 100:g}-percentage-point transfers using the same frozen sample. It records policy feasibility, actual risk change and local marginal approximation for Normal VaR/ES and Historical ES. Infeasible transfers are retained with reasons. This is a sensitivity grid, not an optimisation or a chosen trade. Expected return, income, costs, stress outcomes and the client's objectives must also be considered before changing allocation.",
        "Risk changes exclude transaction costs and use fixed distribution inputs. Read marginal_status and marginal_warning: a tie-selected ES subgradient may not equal a particular directional derivative. Exact repricing is the relevant finite-transfer comparison.",
        "",
        "## Historical crisis replays",
        "",
        "Every replay starts with the same USD NAV immediately before its first return. Units are held fixed; asset weights drift. There are no trades, trading costs or withdrawals. Missing calendar sessions withhold the entire replay. The 2008 replay uses allocations fitted later and is explicitly retrospective, not evidence of an implementable 2008 investment strategy. All replays are scenario comparisons, even when weights were already estimable.",
        "Drawdown is a positive loss fraction of the relevant running peak. Its USD amount is peak NAV minus trough NAV at the date of the maximum percentage drawdown; it is not necessarily 10m times that percentage. Terminal gain/loss and drawdown are different. The periods have different lengths and cannot be compared directly to one-day VaR/ES as if horizons matched.",
        "",
        "| Scenario | Portfolio | Sessions observed / required | Terminal loss USD | Maximum drawdown | Drawdown USD | > review level | Status |",
        "|---|---|---:|---:|---:|---:|---|---|",
    ]
    for r in frames["historical_summary"].itertuples():
        lines.append(
            f"| {r.scenario} | {r.strategy} | {r.observed_sessions}/{r.expected_sessions} | {number(r.terminal_loss_usd)} | {number(r.maximum_drawdown_fraction, True)} | {number(r.drawdown_usd_at_max_fraction)} | {r.review_trigger_breached if pd.notna(r.review_trigger_breached) else 'unavailable'} | {r.status} |"
        )
        if r.status != "ok":
            lines += ["", f"Unavailable {r.scenario}/{r.strategy}: {r.warning}", ""]
    lines += [
        "",
        "## Proposed hypothetical shock",
        "",
        context["shock_narrative"],
        "",
        "Base shock assumptions and development-only worst daily returns are below. The historical minimum is context, not a calibrated joint event or probability. All ETF shocks occur together. The reported multipliers are severity sensitivity, not confidence levels. No additional correlation multiplier is applied to the already joint shock. Team review of narrative and severity remains pending.",
        "",
        "| ETF | Base hypothetical return | Development worst daily return |",
        "|---|---:|---:|",
    ]
    for r in frames["scenario_shocks"].itertuples():
        lines.append(
            f"| {r.ticker} | {number(r.base_shock_return, True)} | {number(r.development_worst_daily_return, True)} |"
        )
    lines += [
        "",
        "| Portfolio | Multiplier | Loss | Loss USD | > scenario review level |",
        "|---|---:|---:|---:|---|",
    ]
    for r in frames["hypothetical_summary"].itertuples():
        lines.append(
            f"| {r.strategy} | {r.multiplier:g} | {number(r.loss_fraction, True)} | {number(r.loss_usd)} | {r.review_trigger_breached} |"
        )
    lines += [
        "",
        "## Interpretation and review",
        "",
        "The 99% one-day ES, crisis drawdown and hypothetical loss review levels are proposed policy assumptions, saved in summary.json. A breach requires discussion, not automatic rejection or approval; a non-breach is not a safety guarantee. Gaussian attribution inherits the model's tail and clustering limitations. Historical tail attribution can change sharply with a few dates. This phase does not supersede the backtesting rejections or validate ES severity forecasts. No liquidity/counterparty model, macro-to-ETF pricing model or spending sustainability analysis is included.",
        "Inspect asset_contributions.csv, sizing_checks.csv, historical_summary.csv (exact boundaries and peak/trough dates), historical_components.csv and hypothetical_components.csv. Complete docs/final/08-contributions-stress/03-manual-stress-check.md before claiming human review or scenario approval.",
    ]
    for chart in charts:
        lines += ["", f"![{chart.removesuffix('.png').replace('_', ' ')}]({chart})"]
    lines += [
        "",
        "References: [Tasche, Euler allocation](https://arxiv.org/abs/0708.2542), [BCBS stress testing principles](https://www.bis.org/publications/201810-guidelines-stress-testing-principles).",
    ]
    return "\n".join(lines) + "\n"
