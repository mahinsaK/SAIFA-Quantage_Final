"""One-command launch preparation: verified reuse and stale/missing artifact recovery."""

from types import SimpleNamespace

import pytest

from commands import run_judge_app
from saifa.data.snapshots import file_hash, write_json
from saifa.domain.dashboard import DashboardDataError


def test_submission_ready_checks_bound_artifacts(tmp_path):
    snapshot = "frozen"
    bundle = tmp_path / "output/app/frozen/bundle.json"
    bundle.parent.mkdir(parents=True)
    bundle.write_text("verified bundle")
    decision = tmp_path / "output/decision/frozen/manifest.json"
    decision.parent.mkdir(parents=True)
    decision.write_text("verified decision")
    folder = tmp_path / "output/pdf/frozen"
    folder.mkdir(parents=True)
    pages = {
        "investment-report.pdf": 12,
        "executive-tear-sheet.pdf": 1,
        "committee-recommendation.pdf": 1,
    }
    files = {}
    for name in pages:
        for filename in (name, name[:-4] + ".md"):
            path = folder / filename
            path.write_text(filename)
            files[filename] = file_hash(path)
    manifest = {
        "status": "complete",
        "snapshot_id": snapshot,
        "source_bundle_sha256": file_hash(bundle),
        "decision_manifest_sha256": file_hash(decision),
        "page_counts": pages,
        "files": files,
    }
    write_json(folder / "submission-manifest.json", manifest)
    assert run_judge_app.submission_ready(tmp_path, snapshot)
    (folder / "executive-tear-sheet.pdf").write_text("changed")
    assert not run_judge_app.submission_ready(tmp_path, snapshot)


def test_prepare_reuses_verified_outputs_without_recalculation(tmp_path, monkeypatch):
    snapshot = tmp_path / "data/snapshots/frozen"
    snapshot.mkdir(parents=True)
    monkeypatch.setattr(run_judge_app, "load_bundle", lambda root, path: SimpleNamespace())
    monkeypatch.setattr(run_judge_app, "load_decision", lambda root, bundle: ({}, {}))
    monkeypatch.setattr(run_judge_app, "submission_ready", lambda root, sid: True)
    monkeypatch.setattr(
        run_judge_app, "build_dashboard", lambda *args, **kwargs: pytest.fail("rebuild")
    )
    monkeypatch.setattr(run_judge_app, "build_decision", lambda *args: pytest.fail("rebuild"))
    monkeypatch.setattr(run_judge_app, "write_submission", lambda *args: pytest.fail("rebuild"))
    monkeypatch.setattr(run_judge_app, "resolve_snapshot", lambda root: snapshot)
    assert run_judge_app.prepare(tmp_path, progress=lambda _: None) == (
        tmp_path / "output/app/frozen/bundle.json"
    )


def test_prepare_rebuilds_missing_stages_in_order(tmp_path, monkeypatch):
    snapshot = tmp_path / "data/snapshots/frozen"
    snapshot.mkdir(parents=True)
    events = []

    def load_bundle(root, path):
        events.append("load app")
        if events.count("load app") == 1:
            raise DashboardDataError("app absent")
        return SimpleNamespace()

    def load_decision(root, bundle):
        events.append("load decision")
        raise DashboardDataError("decision absent")

    monkeypatch.setattr(run_judge_app, "resolve_snapshot", lambda root: snapshot)
    monkeypatch.setattr(run_judge_app, "load_bundle", load_bundle)
    monkeypatch.setattr(run_judge_app, "load_decision", load_decision)
    monkeypatch.setattr(
        run_judge_app, "build_dashboard", lambda *args, **kwargs: events.append("build app")
    )
    monkeypatch.setattr(
        run_judge_app, "build_decision", lambda *args: events.append("build decision")
    )
    monkeypatch.setattr(run_judge_app, "submission_ready", lambda *args: False)
    monkeypatch.setattr(
        run_judge_app, "write_submission", lambda *args: events.append("build PDFs")
    )
    run_judge_app.prepare(tmp_path, progress=lambda _: None)
    assert events == [
        "load app",
        "build app",
        "load app",
        "load decision",
        "build decision",
        "build PDFs",
    ]
