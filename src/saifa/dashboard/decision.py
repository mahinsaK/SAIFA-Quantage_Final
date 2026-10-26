"""Optional verified decision extension; missing/stale evidence is never displayed."""

from pathlib import Path

import pandas as pd
import streamlit as st

from saifa.dashboard.data import inside, read_json, verify_bundle
from saifa.data.snapshots import file_hash
from saifa.domain.dashboard import DashboardBundle, DashboardDataError

DECISION_TABLES = (
    "comparison",
    "backtest_tests",
    "backtest_lights",
    "spending_summary",
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


def decision_summary(bundle: DashboardBundle, strategy: str) -> None:
    root = bundle.manifest_path.resolve().parents[3]
    try:
        summary, tables = load_decision(root, bundle)
    except DashboardDataError as exc:
        st.info(
            "Committee summary unavailable. Prepare it with: "
            "uv run --locked python commands/run_submission.py"
        )
        st.caption(str(exc))
        return
    with st.container(border=True):
        st.subheader("Committee decision - proposed, awaiting human review")
        st.warning(summary["decision"])
        st.caption(
            "This overall decision is fixed across sidebar choices. The spending "
            "comparison below follows the selected portfolio; risk controls retain "
            "their existing scope."
        )
        st.write(summary["inflation_limitation"])
        st.metric("Observed real-growth objective", "Not established")
        selected = tables["spending_summary"].query("strategy == @strategy").copy()
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
            alt="Selected portfolio spending outcomes under assumed inflation",
        )
        st.caption(summary["payment_rule"])
        st.caption(summary["objective_note"] + " " + summary["horizon_note"])
        with st.expander("Funding rules and decisions still required"):
            st.write(summary["funding_rule"])
            for condition in summary["conditions"]:
                st.write("- " + condition)
        st.download_button(
            "Download spending comparison",
            selected.to_csv(index=False),
            file_name=f"{strategy}_spending.csv",
            mime="text/csv",
        )
