"""Optional verified decision extension; missing/stale evidence is never displayed."""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

from saifa.dashboard.data import inside, read_json, verify_bundle
from saifa.dashboard.presentation import PORTFOLIO_COLORS
from saifa.dashboard.visual_data import observed_growth_chart_data
from saifa.data.snapshots import file_hash
from saifa.domain.dashboard import STRATEGIES, DashboardBundle, DashboardDataError

DECISION_TABLES = (
    "comparison",
    "backtest_tests",
    "backtest_lights",
    "spending_summary",
    "observed_real",
    "spending_paths",
    "spending_payments",
)


def load_decision(root: Path, bundle: DashboardBundle) -> tuple[dict, dict[str, pd.DataFrame]]:
    folder = root / "output/decision" / bundle.manifest["snapshot_id"]
    manifest = read_json(folder / "manifest.json")
    try:
        if manifest.get("status") != "complete" or manifest.get("schema_version") != 1:
            raise DashboardDataError("Decision evidence is incomplete")
        if manifest["source_bundle_sha256"] != verify_bundle(root, bundle.manifest_path):
            raise DashboardDataError("Decision evidence refers to an older app bundle")
        if manifest["snapshot_id"] != bundle.manifest["snapshot_id"]:
            raise DashboardDataError("Decision snapshot differs")
        required = {"summary.json"} | {f"{name}.csv" for name in DECISION_TABLES}
        if set(manifest["files"]) != required:
            raise DashboardDataError("Decision file manifest is incomplete")
        for name, digest in manifest["files"].items():
            if file_hash(inside(folder, name)) != digest:
                raise DashboardDataError(f"Decision file changed: {name}")
        for name, digest in manifest["source_files"].items():
            if file_hash(inside(root, name)) != digest:
                raise DashboardDataError(f"Decision source changed: {name}")
        summary = read_json(folder / "summary.json")
        if summary["snapshot_id"] != bundle.manifest["snapshot_id"]:
            raise DashboardDataError("Decision summary snapshot differs")
        tables = {
            name: pd.read_csv(folder / f"{name}.csv", float_precision="round_trip")
            for name in DECISION_TABLES
        }
        return summary, tables
    except (OSError, KeyError, TypeError, ValueError) as exc:
        raise DashboardDataError(f"Decision evidence unavailable: {exc}") from exc


def decision_evidence(bundle: DashboardBundle) -> tuple[dict, dict[str, pd.DataFrame]] | None:
    root = bundle.manifest_path.resolve().parents[3]
    try:
        return load_decision(root, bundle)
    except DashboardDataError as exc:
        st.info(
            "Committee summary unavailable. Prepare it with: "
            "uv run --locked python commands/run_submission.py "
            "(or launch with python run_with_pip.py)"
        )
        st.caption(str(exc))
        return None


def decision_banner(summary: dict) -> None:
    with st.container(border=True):
        st.subheader("Team recommendation · proposed policy")
        st.warning(summary["decision"])
        st.caption(
            "Team position supplied on 31 October 2026. Independent review and client/committee "
            "approval remain pending. This recommendation is fixed across portfolio selections."
        )


def spending_sensitivity(summary: dict, tables: dict[str, pd.DataFrame], strategy: str) -> None:
    selected = tables["spending_summary"].query("strategy == @strategy").copy()
    example = selected.loc[selected.inflation_assumption == 0.02]
    observed = tables["observed_real"].set_index("strategy").loc[strategy]
    st.subheader("Purchasing power and spending", anchor="portfolio-spending")
    with st.container(border=True):
        st.markdown("**Observed purchasing power · before withdrawals**")
        with st.container(horizontal=True):
            st.metric(
                "Observed real growth / year", f"{observed.annualised_real_growth:.2%}", border=True
            )
            st.metric(
                "3% objective in observed period",
                "Met" if observed.objective_met_in_observed_period else "Below",
                border=True,
            )
            st.metric("Ending real wealth", f"${observed.ending_real_wealth:,.0f}", border=True)
        st.caption(
            f"{observed.start_date} to {observed.end_date}; costed NAV, no withdrawals. "
            f"Monthly FRED {summary['cpi_source']['series']} from {observed.cpi_start_month} "
            f"to {observed.cpi_end_month}. This observed period is shorter than the proposed ten years."
        )
        try:
            growth, objective = observed_growth_chart_data(tables["observed_real"])
        except DashboardDataError as exc:
            st.warning(f"Portfolio real-growth comparison unavailable: {exc}")
        else:
            bars = (
                alt.Chart(growth)
                .mark_bar()
                .encode(
                    x=alt.X("Portfolio:N", sort=list(STRATEGIES.values()), title=None),
                    y=alt.Y("Real growth (% / year):Q", title="Annual real growth (%)"),
                    color=alt.Color(
                        "Portfolio:N",
                        scale=alt.Scale(
                            domain=list(STRATEGIES.values()), range=list(PORTFOLIO_COLORS.values())
                        ),
                        legend=None,
                    ),
                    tooltip=["Portfolio:N", alt.Tooltip("Real growth (% / year):Q", format=".2f")],
                )
            )
            target = (
                alt.Chart(pd.DataFrame({"Proposed objective (%)": [objective]}))
                .mark_rule(color="#B14F43", strokeDash=[5, 4], strokeWidth=2)
                .encode(y="Proposed objective (%):Q")
            )
            st.altair_chart(
                (bars + target).properties(height=230),
                width="stretch",
                alt="Observed annual real growth for all three portfolios compared with the proposed objective over the shorter historical period",
            )
            st.caption(
                f"Dashed line: proposed {objective:g}% annual real-growth objective. "
                "The observed comparison ends with September 2026 CPI and excludes withdrawals; "
                "it does not establish ten-year success or failure."
            )
        st.markdown("**Illustrative annual spending · 2% assumed inflation**")
        with st.container(horizontal=True):
            if not example.empty:
                row = example.iloc[0]
                st.metric(
                    "Scenario-real wealth after spending",
                    f"${row.ending_scenario_real_wealth:,.0f}",
                    border=True,
                )
                st.metric(
                    "Real remaining-capital growth / year",
                    f"{row.annualised_real_remaining_capital_growth:.2%}",
                    border=True,
                )
        st.caption(
            "Spending figures follow the selected portfolio. The inflation rate is an assumption, "
            "not observed CPI. Actual client spending and ten-year sustainability remain unknown."
        )
        with st.expander("See all spending scenarios, assumptions and decisions required"):
            st.write(summary["inflation_limitation"])
            display = pd.DataFrame(
                {
                    "Assumed inflation": selected.inflation_assumption.map(lambda x: f"{x:.0%}"),
                    "Ending nominal wealth (USD)": selected.ending_nominal_wealth,
                    "Ending scenario-real wealth (USD)": selected.ending_scenario_real_wealth,
                    "Total spending paid (USD)": selected.total_paid,
                    "Real remaining-capital growth (%) / year": selected.annualised_real_remaining_capital_growth
                    * 100,
                    "At least 3% after spending? (scenario only)": selected.meets_after_spending_objective,
                }
            )
            st.dataframe(
                display,
                hide_index=True,
                width="stretch",
                column_config={
                    "Ending nominal wealth (USD)": st.column_config.NumberColumn(format="$%.2f"),
                    "Ending scenario-real wealth (USD)": st.column_config.NumberColumn(
                        format="$%.2f"
                    ),
                    "Total spending paid (USD)": st.column_config.NumberColumn(format="$%.2f"),
                    "Real remaining-capital growth (%) / year": st.column_config.NumberColumn(
                        format="%.2f%%"
                    ),
                },
                alt="Selected portfolio spending outcomes under assumed inflation",
            )
            st.caption(summary["payment_rule"])
            st.caption(summary["objective_note"] + " " + summary["horizon_note"])
            st.write(summary["funding_rule"])
            for condition in summary["conditions"]:
                st.write("- " + condition)
            st.download_button(
                "Download observed real-growth evidence",
                tables["observed_real"].to_csv(index=False),
                file_name="observed_real_growth.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download spending comparison",
                selected.to_csv(index=False),
                file_name=f"{strategy}_spending.csv",
                mime="text/csv",
            )


def decision_summary(bundle: DashboardBundle, strategy: str) -> None:
    """Standalone composition used by reviews and component tests."""
    evidence = decision_evidence(bundle)
    if evidence is not None:
        summary, tables = evidence
        decision_banner(summary)
        spending_sensitivity(summary, tables, strategy)
