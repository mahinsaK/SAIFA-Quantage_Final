"""Prepare missing frozen research outputs, then launch the judge-facing app.

From the repository root: uv run --locked python commands/run_judge_app.py
No market data is downloaded. The first preparation may take several minutes.
"""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".cache/matplotlib"))
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".cache"))

from saifa.application.dashboard_pipeline import build_dashboard
from saifa.application.decision_pipeline import build_decision
from saifa.application.research_pipeline import build_research
from saifa.dashboard.data import load_bundle
from saifa.dashboard.decision import load_decision
from saifa.dashboard.research_data import load_research
from saifa.data.snapshots import file_hash, resolve_snapshot
from saifa.domain.dashboard import DashboardDataError
from saifa.reporting.submission import write_submission


def submission_ready(root: Path, snapshot_id: str) -> bool:
    """Check every published PDF against the same verified app and decision evidence."""
    from saifa.dashboard.data import read_json

    bundle_path = root / "output/app" / snapshot_id / "bundle.json"
    decision_path = root / "output/decision" / snapshot_id / "manifest.json"
    folder = root / "output/pdf" / snapshot_id
    manifest = read_json(folder / "submission-manifest.json")
    if (
        manifest.get("status") != "complete"
        or manifest.get("snapshot_id") != snapshot_id
        or manifest.get("source_bundle_sha256") != file_hash(bundle_path)
        or manifest.get("decision_manifest_sha256") != file_hash(decision_path)
    ):
        return False
    pages = manifest.get("page_counts", {})
    if (
        not isinstance(pages, dict)
        or set(pages)
        != {"investment-report.pdf", "executive-tear-sheet.pdf", "committee-recommendation.pdf"}
        or not isinstance(pages["investment-report.pdf"], int)
        or not 7 <= pages["investment-report.pdf"] <= 15
        or pages["executive-tear-sheet.pdf"] != 1
        or pages["committee-recommendation.pdf"] != 1
    ):
        return False
    expected_files = {name for name in pages for name in (name, name[:-4] + ".md")}
    if set(manifest.get("files", {})) != expected_files:
        return False
    return all(file_hash(folder / name) == digest for name, digest in manifest["files"].items())


def prepare(root: Path, progress=print) -> Path:
    snapshot = resolve_snapshot(root)
    bundle_path = root / "output/app" / snapshot.name / "bundle.json"
    try:
        bundle = load_bundle(root, bundle_path)
        progress("Verified existing frozen app results.")
    except (DashboardDataError, OSError, ValueError) as exc:
        progress(f"Preparing frozen app results: {exc}")
        build_dashboard(root, snapshot, progress=progress)
        bundle = load_bundle(root, bundle_path)
    try:
        load_decision(root, bundle)
        progress("Verified existing committee evidence.")
    except (DashboardDataError, OSError, ValueError) as exc:
        progress(f"Preparing committee evidence: {exc}")
        build_decision(root, snapshot)
    try:
        ready = submission_ready(root, snapshot.name)
    except (DashboardDataError, OSError, ValueError):
        ready = False
    if not ready:
        progress("Preparing report and one-page documents from verified evidence...")
        write_submission(root, snapshot)
    try:
        load_research(root, bundle)
        progress("Verified optional portfolio research lab.")
    except (DashboardDataError, OSError, ValueError) as exc:
        progress(f"Preparing optional research lab: {exc}")
        try:
            build_research(root, snapshot, progress=progress)
        except Exception as research_error:  # noqa: BLE001 - optional experimental stage must not hide the core app.
            progress(
                f"Research lab unavailable: {research_error}. Core frozen app remains available."
            )
    progress("Offline research outputs are ready. Opening the app...")
    return bundle_path


def main() -> int:
    try:
        prepare(ROOT, progress=lambda message: print(message, flush=True))
    except Exception as exc:  # noqa: BLE001 - CLI error boundary
        print(f"App preparation failed: {exc}", file=sys.stderr)
        print(
            "Restore the included frozen snapshot or inspect the printed validation error.",
            file=sys.stderr,
        )
        return 1
    try:
        return subprocess.call(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(ROOT / "app.py"),
                "--server.address",
                "127.0.0.1",
            ],
            cwd=ROOT,
        )
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
