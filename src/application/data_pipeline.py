"""Rebuild audited data products from a verified frozen snapshot."""

from pathlib import Path

import pandas as pd

from src.data.diagnostics import stationarity_table
from src.data.preparation import align_risk_free, audit_prices, calculate_returns, trading_sessions
from src.data.snapshots import file_hash, load_snapshot, write_json


def build_data(root: Path, snapshot: Path) -> Path:
    config, manifest, frames, rates = load_snapshot(snapshot)
    output = root / "output" / "data" / snapshot.name
    output.mkdir(parents=True, exist_ok=True)
    status = {"snapshot_id": snapshot.name, "status": "building"}
    write_json(output / "status.json", status)
    try:
        audit = audit_prices(frames, config, trading_sessions(config))
        audit.coverage.to_csv(output / "coverage.csv", index=False)
        audit.flags.to_csv(output / "quality_flags.csv", index=False)
        errors = audit.flags.loc[audit.flags.severity == "error"]
        if not errors.empty:
            raise ValueError(f"{len(errors)} blocking data flags; see quality_flags.csv")
        simple, log = calculate_returns(audit.prices)
        risk_free = align_risk_free(rates, audit.prices.index, config.max_rate_age_days)
        adf = stationarity_table(log)
        for name, frame in {
            "adjusted_prices": audit.prices,
            "simple_returns": simple,
            "log_returns": log,
            "risk_free_returns": risk_free,
        }.items():
            frame.to_csv(output / f"{name}.csv", index_label="Date", float_format="%.17g")
        adf.to_csv(output / "stationarity.csv", index=False)
        review_count = int((audit.flags.severity == "review").sum())
        source_root = Path(__file__).resolve().parents[2]
        code_files = sorted((source_root / "src").rglob("*.py")) + [source_root / "run_data.py"]
        flag_counts = {str(k): int(v) for k, v in audit.flags.kind.value_counts().items()}
        summary = {
            "snapshot_id": snapshot.name,
            "snapshot_manifest_sha256": file_hash(snapshot / "manifest.json"),
            "config": manifest["config"],
            "prices": len(audit.prices),
            "returns": len(simple),
            "first_price": str(audit.prices.index[0].date()),
            "first_return": str(simple.index[0].date()),
            "last_return": str(simple.index[-1].date()),
            "blocking_flags": 0,
            "review_flags": review_count,
            "flags_by_kind": flag_counts,
            "code_sha256": {str(p.relative_to(source_root)): file_hash(p) for p in code_files},
            "dependency_lock_sha256": file_hash(source_root / "uv.lock"),
            "quality_review_status": "human_review_pending"
            if review_count
            else "no_heuristic_flags",
            "crisis_coverage": {
                name: bool(
                    audit.prices.index[0] <= pd.Timestamp(start)
                    and audit.prices.index[-1] >= pd.Timestamp(end)
                )
                for name, start, end in [
                    ("2008_GFC", "2008-01-01", "2008-12-31"),
                    ("March_2020", "2020-03-01", "2020-03-31"),
                    ("2022_rate_shock", "2022-01-01", "2022-12-30"),
                ]
            },
            "outputs_sha256": {p.name: file_hash(p) for p in sorted(output.glob("*.csv"))},
        }
        write_json(output / "summary.json", summary)
        report = f"""# Data quality report

Snapshot: {snapshot.name}

- Common price window: {summary["first_price"]} to {summary["last_return"]}.
- {summary["prices"]:,} price sessions; {summary["returns"]:,} daily return observations per ETF.
- Blocking flags: 0. Review flags retained: {review_count}. Human event validation remains pending.
- Flag counts by type: {flag_counts}.
- Coverage starts at the latest first valid ETF quote; leading unavailable history is excluded explicitly (see coverage.csv). It is not backfilled or declared a verified inception date.
- XNYS is the common US trading-session calendar proxy for these US-listed ETFs. Foreign underlying-market holidays do not remove valid US ETF quotes.
- No missing session prices were filled, no returns bridged missing quotes and no outliers deleted.
- Adjusted close drives returns. Close, dividends and split fields remain in the snapshot for adjustment review; adjustments are not independent vendor verification.
- Simple return: P[t]/P[t-1] - 1. Log return: log(P[t]/P[t-1]). Both are asset returns, not portfolio returns.
- FRED DGS3MO is an annual investment-basis percentage yield. Approximate cash accrual is yield/100 * elapsed calendar days/365; log accrual is log(1 + simple accrual).
- Rate observation dates must strictly precede the return period's start, with at most {config.max_rate_age_days} calendar days of age at start. This lag is conservative, but does not reconstruct historical release timestamps or vintages.
- ADF uses a constant, AIC lag selection and 5% significance. Full-sample diagnostics are descriptive; repeat within training windows. Rejecting a unit root does not establish constant volatility or absence of structural breaks.
- Price jumps, flat runs, adjustment changes and rolling volatility shifts are review heuristics, not proof of errors. See quality_flags.csv; no human review is claimed.
- Crisis coverage only confirms date coverage, not completion of stress testing.
- Download dates do not define an approved train/test split. No allocation or risk-model decision is made here.

See docs/final/data-methodology.md for provenance, review rules and limitations.
"""
        (output / "quality_report.md").write_text(report, encoding="utf-8")
        status.update(status="complete", review_flags=review_count)
    except Exception as exc:
        status.update(status="failed", error=f"{type(exc).__name__}: {exc}")
        write_json(output / "status.json", status)
        raise
    write_json(output / "status.json", status)
    return output
