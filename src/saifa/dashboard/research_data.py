"""Fail-closed verification and bounded cached parsing of optional research results."""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

from saifa.dashboard.data import inside, read_json, verify_bundle
from saifa.data.snapshots import file_hash
from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.domain.dashboard import CONFIDENCES, STRATEGIES, DashboardBundle, DashboardDataError
from saifa.domain.research import (
    RESEARCH_PORTFOLIOS,
    RESEARCH_TABLES,
    VOLATILITY_METHODS,
    ResearchEvidence,
)
from saifa.models.optimisation import validate_policy_weights


def _grid(frame: pd.DataFrame, keys: list[str], groups: list) -> None:
    actual = pd.MultiIndex.from_frame(frame[keys])
    expected = pd.MultiIndex.from_product(groups)
    if actual.has_duplicates or set(actual) != set(expected):
        raise DashboardDataError(f"Incomplete/duplicate research comparisons: {keys}")


def validate_research(evidence: ResearchEvidence, bundle: DashboardBundle) -> None:
    tables = evidence.tables
    policy = OptimisationConfig(**evidence.summary["portfolio_config"])
    weights = tables["allocation_weights"]
    _grid(weights, ["strategy"], [RESEARCH_PORTFOLIOS])
    for _, row in weights.iterrows():
        validate_policy_weights(row.loc[list(UNIVERSE)].astype(float), policy)
    metrics = tables["candidate_metrics"]
    _grid(metrics, ["period", "strategy"], [["validation", "evaluation"], RESEARCH_PORTFOLIOS])
    if not np.isfinite(
        metrics[
            ["ending_value", "annualised_return", "annualised_volatility", "maximum_drawdown"]
        ].to_numpy(dtype=float)
    ).all():
        raise DashboardDataError("Unavailable research portfolio performance")
    for _, rows in metrics.groupby("period"):
        if any(
            rows[c].isna().any() or rows[c].nunique() != 1
            for c in ("start_date", "end_date", "initial_capital")
        ):
            raise DashboardDataError("Research performance periods/capital differ")
    forecasts = tables["volatility_forecasts"]
    targets = bundle.tables["backtest"]["forecasts"].forecast_date.astype(str).unique()
    _grid(
        forecasts,
        ["strategy", "method", "confidence", "forecast_date"],
        [STRATEGIES, VOLATILITY_METHODS, CONFIDENCES, targets],
    )
    if (
        not (pd.to_datetime(forecasts.as_of) < pd.to_datetime(forecasts.forecast_date)).all()
        or not (
            pd.to_datetime(forecasts.parameter_fit_end) <= pd.to_datetime(forecasts.as_of)
        ).all()
        or not forecasts.reference_nav.eq(policy.initial_capital).all()
        or not forecasts.horizon_sessions.eq(1).all()
    ):
        raise DashboardDataError("Research risk timing, horizon or NAV differs")
    if not forecasts.status.isin(["ok", "unavailable"]).all():
        raise DashboardDataError("Unknown research forecast status")
    if forecasts.loc[forecasts.status == "ok", ["var_fraction", "es_fraction"]].isna().any().any():
        raise DashboardDataError("Successful research risk row lacks estimates")
    for measure in ("var", "es", "loss"):
        if not np.allclose(
            forecasts[f"{measure}_usd"],
            forecasts[f"{measure}_fraction"] * policy.initial_capital,
            equal_nan=True,
        ):
            raise DashboardDataError("Research risk USD units differ")
    spending = tables["spending_summary"]
    _grid(
        spending,
        ["strategy", "withdrawal_rate", "inflation_annual_spread"],
        [STRATEGIES, [0.02, 0.03, 0.04], [0.0, 0.02]],
    )
    for c in (
        "no_shortfall_fraction",
        "conditional_wilson_low",
        "conditional_wilson_high",
        "preserved_real_capital_fraction",
        "after_spending_3pct_growth_fraction",
    ):
        if not spending[c].between(0, 1).all():
            raise DashboardDataError("Invalid conditional simulation frequency")
    if (spending.conditional_wilson_low > spending.no_shortfall_fraction).any() or (
        spending.conditional_wilson_high < spending.no_shortfall_fraction
    ).any():
        raise DashboardDataError("Conditional sampling interval does not contain its estimate")
    months = evidence.summary["config"]["spending_months"]
    _grid(
        tables["spending_fan"],
        ["strategy", "withdrawal_rate", "inflation_annual_spread", "month"],
        [STRATEGIES, [0.02, 0.03, 0.04], [0.0, 0.02], range(months + 1)],
    )
    _grid(
        tables["cost_metrics"],
        ["period", "strategy", "trade_cost_bps", "additional_annual_fee_bps"],
        [["validation", "evaluation"], RESEARCH_PORTFOLIOS, [0.0, 10.0, 25.0], [0.0, 25.0, 50.0]],
    )
    income = tables["income_summary"]
    _grid(income, ["strategy"], [RESEARCH_PORTFOLIOS])
    if (
        not income.status.isin(["proxy_only", "unavailable"]).all()
        or income.loc[income.status == "unavailable", "distribution_proxy_usd"].notna().any()
    ):
        raise DashboardDataError(
            "Unavailable income must retain its reason without a substitute total"
        )


@st.cache_data(max_entries=2, show_spinner=False)
def _read(folder: str, digest: str) -> ResearchEvidence:
    path = Path(folder)
    return ResearchEvidence(
        read_json(path / "summary.json"),
        {
            name: pd.read_csv(path / f"{name}.csv", float_precision="round_trip")
            for name in RESEARCH_TABLES
        },
    )


def load_research(root: Path, bundle: DashboardBundle) -> ResearchEvidence:
    folder = root / "output/research" / bundle.manifest["snapshot_id"]
    manifest_path = folder / "manifest.json"
    manifest = read_json(manifest_path)
    try:
        if manifest.get("status") != "complete" or manifest.get("schema_version") != 1:
            raise DashboardDataError("Research lab results are incomplete")
        if manifest["snapshot_id"] != bundle.manifest["snapshot_id"]:
            raise DashboardDataError("Research lab snapshot differs")
        if manifest["source_bundle_sha256"] != verify_bundle(root, bundle.manifest_path):
            raise DashboardDataError("Research lab refers to an older base bundle")
        if set(manifest["files"]) != {"summary.json", *[f"{n}.csv" for n in RESEARCH_TABLES]}:
            raise DashboardDataError("Research lab output list is incomplete")
        for name, digest in manifest["files"].items():
            if file_hash(inside(folder, name)) != digest:
                raise DashboardDataError(f"Research output changed: {name}")
        for section in ("source_files", "source_inputs"):
            for name, digest in manifest[section].items():
                if file_hash(inside(root, name)) != digest:
                    raise DashboardDataError(f"Research source changed: {name}")
        result = _read(str(folder), file_hash(manifest_path))
        if (
            result.summary["snapshot_id"] != bundle.manifest["snapshot_id"]
            or result.summary["portfolio_config"] != bundle.metadata["portfolio"]["config"]
        ):
            raise DashboardDataError("Research policy/snapshot differs")
        validate_research(result, bundle)
        return result
    except (KeyError, OSError, ValueError, TypeError) as exc:
        raise DashboardDataError(f"Research lab evidence unavailable: {exc}") from exc
