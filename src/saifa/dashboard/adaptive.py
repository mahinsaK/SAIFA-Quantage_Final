"""Verified, separately scoped annual-portfolio experiment on the Portfolio page."""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from saifa.dashboard.data import inside, read_json, verify_bundle
from saifa.dashboard.presentation import PORTFOLIO_COLORS, money, percent
from saifa.data.snapshots import file_hash
from saifa.domain.adaptive import ADAPTIVE_STRATEGIES, ADAPTIVE_TABLES, AdaptiveEvidence
from saifa.domain.config import UNIVERSE
from saifa.domain.dashboard import DashboardBundle, DashboardDataError


def load_adaptive(root: Path, bundle: DashboardBundle) -> AdaptiveEvidence:
    folder = root / "output/adaptive" / bundle.manifest["snapshot_id"]
    manifest = read_json(folder / "manifest.json")
    try:
        if manifest.get("status") != "complete" or manifest.get("schema_version") != 1:
            raise DashboardDataError("Annual strategy results are incomplete")
        if manifest["snapshot_id"] != bundle.manifest["snapshot_id"]:
            raise DashboardDataError("Annual strategy snapshot differs")
        if manifest["source_bundle_sha256"] != verify_bundle(root, bundle.manifest_path):
            raise DashboardDataError("Annual strategy refers to an older base bundle")
        if set(manifest["files"]) != {"summary.json", *[f"{n}.csv" for n in ADAPTIVE_TABLES]}:
            raise DashboardDataError("Annual strategy output manifest is incomplete")
        for name, digest in manifest["files"].items():
            if file_hash(inside(folder, name)) != digest:
                raise DashboardDataError(f"Annual strategy output changed: {name}")
        for section in ("source_files", "source_inputs"):
            for name, digest in manifest[section].items():
                if file_hash(inside(root, name)) != digest:
                    raise DashboardDataError(f"Annual strategy source changed: {name}")
        summary = read_json(folder / "summary.json")
        if (
            summary["snapshot_id"] != bundle.manifest["snapshot_id"]
            or summary["config"]["portfolio"] != bundle.metadata["portfolio"]["config"]
        ):
            raise DashboardDataError("Annual strategy policy or snapshot differs")
        tables = {
            n: pd.read_csv(folder / f"{n}.csv", float_precision="round_trip")
            for n in ADAPTIVE_TABLES
        }
        metrics = tables["metrics"]
        grid = pd.MultiIndex.from_frame(metrics[["period", "strategy"]])
        expected = pd.MultiIndex.from_product([["validation", "evaluation"], ADAPTIVE_STRATEGIES])
        if grid.has_duplicates or set(grid) != set(expected):
            raise DashboardDataError("Annual strategy comparisons are incomplete")
        numeric = metrics[
            [
                "ending_value",
                "annualised_return",
                "annualised_volatility",
                "maximum_drawdown",
                "total_transaction_cost",
            ]
        ]
        if not np.isfinite(numeric.to_numpy(dtype=float)).all():
            raise DashboardDataError("Annual strategy performance is unavailable")
        return AdaptiveEvidence(summary, tables)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        raise DashboardDataError(f"Annual strategy evidence unavailable: {exc}") from exc


def annual_strategy_section(bundle: DashboardBundle) -> None:
    st.subheader("Annual portfolio re-optimisation", anchor="portfolio-annual")
    root = bundle.manifest_path.resolve().parents[3]
    try:
        evidence = load_adaptive(root, bundle)
    except (DashboardDataError, OSError, ValueError) as exc:
        st.info(
            "Annual strategy results unavailable. Run the normal app launcher to prepare them, "
            "or: uv run --locked python commands/run_adaptive.py"
        )
        st.caption(str(exc))
        return
    render_annual_strategy(evidence)


def render_annual_strategy(evidence: AdaptiveEvidence) -> None:
    summary, tables = evidence.summary, evidence.tables
    config = summary["config"]
    st.caption("Retrospective experiment · adaptive risk validation pending.")
    explanation = st.expander("Read explanation, methodology and limitations", expanded=False)
    with explanation:
        st.write(
            "Can updating targets once a year improve on frozen allocations after trading costs? "
            "The evaluation period was already viewed before this experiment was designed; "
            "it is not a new untouched test."
        )
        st.write(summary["execution_rule"])
        st.caption(summary["scope"])
        st.caption(summary["comparison_limitation"])
        st.info(summary["risk_scope"])
    period = st.selectbox(
        "Annual strategy comparison period",
        ["evaluation", "validation"],
        format_func=str.capitalize,
        key="annual_period",
    )
    objective = st.selectbox(
        "Annual strategy objective",
        ["minimum_volatility", "maximum_sharpe"],
        format_func=lambda s: ADAPTIVE_STRATEGIES[f"annual_{s}"],
        key="annual_objective",
    )
    metrics = tables["metrics"].loc[tables["metrics"].period == period]
    first = metrics.iloc[0]
    st.caption(
        f"{first.start_date} to {first.end_date}; initial {money(first.initial_capital)} each; "
        f"{config['portfolio']['transaction_cost_bps']:g} bps on gross purchases and sales."
    )
    display = pd.DataFrame(
        {
            "Portfolio": metrics.strategy.map(ADAPTIVE_STRATEGIES),
            "Ending value (USD)": metrics.ending_value.map(money),
            "Annualised return": metrics.annualised_return.map(percent),
            "Annualised volatility": metrics.annualised_volatility.map(percent),
            "Largest drawdown": (-metrics.maximum_drawdown).map(percent),
            "Trading costs (USD)": metrics.total_transaction_cost.map(money),
            "Annual target updates after funding": metrics.annual_target_updates,
        }
    )
    st.dataframe(
        display,
        hide_index=True,
        width="stretch",
        alt="Same-period costed frozen and annual portfolio comparison",
    )
    strategies = ["baseline_40_60", objective, f"annual_{objective}"]
    daily = tables["daily"]
    selected = daily.loc[(daily.period == period) & daily.strategy.isin(strategies)].copy()
    selected["Date"] = pd.to_datetime(selected.Date)
    paths = selected.pivot(index="Date", columns="strategy", values="nav").reindex(
        columns=strategies
    )
    paths.columns = paths.columns.map(ADAPTIVE_STRATEGIES)
    st.line_chart(
        paths / first.initial_capital * 100,
        color=[PORTFOLIO_COLORS["baseline_40_60"], PORTFOLIO_COLORS[objective], "#7657A6"],
        y_label="Value index (initial capital = 100)",
        alt="Baseline and matched frozen versus annual target wealth paths after costs",
    )
    comparison = tables["comparison"]
    change = comparison.loc[
        (comparison.period == period) & (comparison.objective == objective)
    ].iloc[0]
    with explanation:
        st.markdown(
            f"**Annual minus frozen · {ADAPTIVE_STRATEGIES[f'annual_{objective}']}:** "
            f"ending wealth {change.ending_value_change_usd:+,.2f} USD; "
            f"annual return {change.annualised_return_change_fraction * 100:+.2f} percentage points; "
            f"volatility {change.annualised_volatility_change_fraction * 100:+.2f} points; "
            f"drawdown loss {change.drawdown_loss_change_fraction * 100:+.2f} points; "
            f"trading costs {change.trading_cost_change_usd:+,.2f} USD."
        )
        st.caption(
            "Negative volatility/drawdown changes mean lower measured risk. These realised differences do not establish future superiority."
        )
    with st.expander("Annual targets, training dates and accounting evidence"):
        targets = tables["annual_targets"]
        targets = targets.loc[
            (targets.strategy == f"annual_{objective}")
            & targets.execution_date.between(first.start_date, first.end_date)
        ]
        st.dataframe(
            targets,
            hide_index=True,
            width="stretch",
            column_config={
                **{
                    ticker: st.column_config.NumberColumn(f"{ticker} target", format="percent")
                    for ticker in UNIVERSE
                },
                "expected_return": st.column_config.NumberColumn(
                    "Estimated annual return", format="percent"
                ),
                "estimated_volatility": st.column_config.NumberColumn(
                    "Estimated annual volatility", format="percent"
                ),
                "annual_risk_free": st.column_config.NumberColumn(
                    "Training risk-free rate", format="percent"
                ),
            },
            alt="Annual target weights, strictly preceding training windows and solver status",
        )
        st.caption(
            "Targets are displayed as percentages; downloaded ETF columns are fractions (0.60 = 60%). Training estimates are before trading costs and are not forecasts or realised returns."
        )
        st.caption(summary["failure_rule"])
        st.download_button(
            "Download annual target audit",
            targets.to_csv(index=False),
            file_name=f"{period}_annual_{objective}_targets.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download annual comparison paths",
            selected.to_csv(index=False),
            file_name=f"{period}_annual_{objective}_paths.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download all annual strategy metrics",
            tables["metrics"].to_csv(index=False),
            file_name="annual_strategy_metrics.csv",
            mime="text/csv",
        )
