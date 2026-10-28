"""Decision extension integrity and judge-facing evidence selection."""

import json

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest
from test_dashboard import forecasts as forecasts  # noqa: PLC0414 - fixture export
from test_dashboard import prepared as prepared  # noqa: PLC0414 - fixture export

from saifa.application.decision_pipeline import git_provenance
from saifa.dashboard.data import load_bundle
from saifa.dashboard.decision import DECISION_TABLES, load_decision
from saifa.data.snapshots import file_hash, write_json
from saifa.domain.dashboard import DashboardDataError
from saifa.domain.decision import CONDITIONS, CPI_LIMITATION, DECISION
from saifa.reporting.submission import Document


def extension(root, bundle):
    folder = root / "output/decision/test"
    folder.mkdir(parents=True)
    write_json(folder / "summary.json", {"snapshot_id": "test"})
    for name in DECISION_TABLES:
        pd.DataFrame({"fixture": [1]}).to_csv(folder / f"{name}.csv", index=False)
    manifest = {
        "status": "complete",
        "schema_version": 1,
        "snapshot_id": "test",
        "source_bundle_sha256": file_hash(bundle.manifest_path),
        "source_files": {},
        "files": {p.name: file_hash(p) for p in folder.iterdir()},
    }
    write_json(folder / "manifest.json", manifest)
    return folder


def test_decision_extension_reads_only_matching_verified_bundle(prepared):
    root, path, _ = prepared
    bundle = load_bundle(root, path)
    extension(root, bundle)
    summary, tables = load_decision(root, bundle)
    assert summary["snapshot_id"] == "test"
    assert set(tables) == set(DECISION_TABLES)


@pytest.mark.parametrize("failure", ["tampered", "stale", "missing", "code_changed"])
def test_decision_extension_refuses_invalid_evidence(prepared, failure):
    root, path, _ = prepared
    bundle = load_bundle(root, path)
    folder = extension(root, bundle)
    if failure == "tampered":
        (folder / "spending_summary.csv").write_text("modified\n")
    elif failure == "missing":
        (folder / "spending_summary.csv").unlink()
    else:
        manifest = json.loads((folder / "manifest.json").read_text())
        if failure == "stale":
            manifest["source_bundle_sha256"] = "old"
        else:
            (root / "source.py").write_text("new code")
            manifest["source_files"] = {"source.py": "old"}
        write_json(folder / "manifest.json", manifest)
    with pytest.raises(DashboardDataError):
        load_decision(root, bundle)


def test_decision_ui_follows_portfolio_and_shows_observed_cpi_growth(monkeypatch):
    summary = {
        "decision": DECISION,
        "inflation_limitation": CPI_LIMITATION,
        "conditions": CONDITIONS,
        "payment_rule": "Hypothetical annual payments",
        "objective_note": "Stricter after-spending test",
        "horizon_note": "Under five years",
        "funding_rule": "Proportional sales",
        "cpi_source": {"series": "CPIAUCSL"},
    }
    table = pd.DataFrame(
        [
            {
                "strategy": s,
                "inflation_assumption": p,
                "ending_nominal_wealth": n,
                "ending_scenario_real_wealth": n / 1.1,
                "total_paid": 300,
                "annualised_real_remaining_capital_growth": 0.01,
                "meets_after_spending_objective": False,
            }
            for s, n in [("baseline_40_60", 1000), ("minimum_volatility", 1200)]
            for p in (0, 0.02, 0.04)
        ]
    )
    monkeypatch.setattr(
        "saifa.dashboard.decision.load_decision",
        lambda *args: (
            summary,
            {
                "spending_summary": table,
                "observed_real": pd.DataFrame(
                    [
                        {
                            "strategy": strategy,
                            "start_date": "2022-01-03",
                            "end_date": "2026-09-30",
                            "cpi_start_month": "2022-01-01",
                            "cpi_end_month": "2026-09-01",
                            "annualised_real_growth": growth,
                            "objective_met_in_observed_period": False,
                            "ending_real_wealth": wealth,
                        }
                        for strategy, growth, wealth in [
                            ("baseline_40_60", 0.0068, 10325),
                            ("minimum_volatility", 0.0254, 11263),
                        ]
                    ]
                ),
            },
        ),
    )

    def script():
        from pathlib import Path
        from types import SimpleNamespace

        import streamlit as st

        from saifa.dashboard.decision import decision_summary

        selected = st.selectbox("Portfolio", ["baseline_40_60", "minimum_volatility"])
        decision_summary(
            SimpleNamespace(manifest_path=Path("/root/output/app/test/bundle.json")), selected
        )

    app = AppTest.from_function(script).run()
    assert not app.exception
    assert app.metric[0].value == "0.68%"
    assert app.metric[1].value == "Below"
    assert app.dataframe[0].value["Ending nominal wealth (USD)"].iloc[0] == 1000
    app.selectbox[0].select("minimum_volatility").run()
    assert not app.exception
    assert app.metric[0].value == "2.54%"
    assert app.dataframe[0].value["Ending nominal wealth (USD)"].iloc[0] == 1200
    assert "Defer implementation" in app.warning[0].value


def test_document_page_count_and_readable_source(tmp_path):
    doc = Document("Test", "test")
    doc.page("One", "Context")
    doc.p("A & B < C")
    doc.page("Two", "Context")
    doc.table(["Unit", "Value"], [["USD", "$1,000"]])
    assert doc.save(tmp_path / "test.pdf") == 2
    assert (tmp_path / "test.pdf").read_bytes().startswith(b"%PDF")
    assert "A & B < C" in (tmp_path / "test.md").read_text()


def test_zip_without_git_still_has_valid_source_provenance(tmp_path):
    assert git_provenance(tmp_path) == (None, None)
