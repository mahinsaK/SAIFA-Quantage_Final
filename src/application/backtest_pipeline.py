"""Rebuild frozen inputs, generate rolling forecasts, then evaluate separate periods."""

import json
from collections.abc import Callable
from dataclasses import asdict
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from src.application.data_pipeline import build_data
from src.application.risk_pipeline import _git_state, _portfolios, _read_returns
from src.data.snapshots import file_hash, write_json
from src.domain.config import UNIVERSE, BacktestConfig, EVTConfig, OptimisationConfig
from src.models.backtesting import basel_traffic_light, christoffersen_test, kupiec_test
from src.models.optimisation import fit_target_allocations
from src.models.walk_forward import walk_forward
from src.reporting.backtesting import plot_backtests, render_backtest_report


def evaluate_forecasts(
    forecasts: pd.DataFrame, config: BacktestConfig
) -> tuple[pd.DataFrame, pd.DataFrame]:
    summaries, lights = [], []
    keys = ["period", "strategy", "method", "confidence"]
    for labels, frame in forecasts.groupby(keys, sort=False):
        frame = frame.sort_values("forecast_date")
        if frame.forecast_date.duplicated().any():
            raise ValueError("Duplicate forecast date in model/portfolio/confidence group")
        dates = pd.DatetimeIndex(pd.to_datetime(frame.forecast_date))
        expected = xcals.get_calendar("XNYS", start=dates[0], end=dates[-1]).sessions.tz_localize(
            None
        )
        if not dates.equals(expected):
            raise ValueError("Forecast rows must retain every consecutive exchange session")
        identity = dict(zip(keys, labels))
        hits = frame.exception.to_numpy(dtype=float)
        coverage = kupiec_test(hits, labels[-1], config.significance)
        independence = christoffersen_test(hits, config.significance, config.minimum_previous_state)
        summaries.append(
            dict(
                **identity,
                start=frame.forecast_date.iloc[0],
                end=frame.forecast_date.iloc[-1],
                significance=config.significance,
                **{f"coverage_{k}": v for k, v in asdict(coverage).items()},
                **{f"independence_{k}": v for k, v in asdict(independence).items()},
            )
        )
        if np.isclose(labels[-1], 0.99, rtol=0, atol=1e-12):
            for i in range(len(frame)):
                start = max(0, i - 249)
                result = basel_traffic_light(hits[start : i + 1], labels[-1])
                lights.append(
                    dict(
                        **identity,
                        start=frame.forecast_date.iloc[start],
                        end=frame.forecast_date.iloc[i],
                        **asdict(result),
                    )
                )
    light_columns = keys + [
        "start",
        "end",
        "observations",
        "exceptions",
        "zone",
        "status",
        "warning",
    ]
    return pd.DataFrame(summaries), pd.DataFrame(lights, columns=light_columns)


def build_backtest(
    root: Path,
    snapshot: Path,
    config: BacktestConfig | None = None,
    evt: EVTConfig | None = None,
    policy: OptimisationConfig | None = None,
    data_builder: Callable = build_data,
    progress: Callable[[int, int], None] | None = None,
) -> Path:
    config, evt, policy = (
        config or BacktestConfig(),
        evt or EVTConfig(),
        policy or OptimisationConfig(),
    )
    if pd.Timestamp(config.start) < pd.Timestamp(policy.development_end_exclusive) or pd.Timestamp(
        config.end_exclusive
    ) > pd.Timestamp(policy.evaluation_end_exclusive):
        raise ValueError(
            "Backtest dates must stay after development and within the declared evaluation boundary"
        )
    # Bootstrap settings are irrelevant here: daily forecasts fit one GPD, without bootstrapping.
    evt_settings = {key: getattr(evt, key) for key in ("threshold_quantile", "minimum_exceedances")}
    settings = {
        "backtest": asdict(config),
        "evt": evt_settings,
        "portfolio": asdict(policy),
        "simulation": "date-seeded scalar projection of Gaussian portfolio loss",
    }
    run_id = sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:12]
    output = root / "output/backtest" / snapshot.name / run_id
    output.mkdir(parents=True, exist_ok=True)
    status = {"status": "building", "snapshot_id": snapshot.name, "run_id": run_id}
    write_json(output / "status.json", status)
    try:
        data_output = data_builder(root, snapshot)
        returns = _read_returns(data_output / "simple_returns.csv")
        if tuple(returns.columns) != UNIVERSE:
            raise ValueError("Backtest requires all seven eligible ETFs")
        rates = _read_returns(data_output / "risk_free_returns.csv").simple_return
        development = returns.loc[returns.index < policy.development_end_exclusive]
        development_rates = rates.loc[rates.index < policy.development_end_exclusive]
        fitted = fit_target_allocations(development, development_rates, policy)
        portfolios = _portfolios(fitted.candidates, policy)
        weights_as_of = str(development.index[-1].date())
        forecasts = walk_forward(
            returns,
            portfolios,
            config,
            evt,
            weights_as_of,
            policy.validation_end_exclusive,
            progress,
        )
        summary, lights = evaluate_forecasts(forecasts, config)
        latest = lights.groupby(["period", "strategy", "method", "confidence"], sort=False).tail(1)
        for name, frame in (
            ("forecasts", forecasts),
            ("test_summary", summary),
            ("basel_rolling", lights),
            ("basel_latest", latest),
        ):
            frame.to_csv(output / f"{name}.csv", index=False, float_format="%.17g")
        pd.DataFrame(portfolios).T.to_csv(
            output / "portfolio_weights.csv", index_label="strategy", float_format="%.17g"
        )
        used = returns.loc[forecasts.window_start.min() : forecasts.forecast_date.max()]
        used.to_csv(output / "returns_used.csv", index_label="Date", float_format="%.17g")
        context = {
            "snapshot_id": snapshot.name,
            "run_id": run_id,
            "start": forecasts.forecast_date.min(),
            "end": forecasts.forecast_date.max(),
            "forecast_sessions": forecasts.forecast_date.nunique(),
            "rows": len(forecasts),
            "weights_as_of": weights_as_of,
            "validation_end_exclusive": policy.validation_end_exclusive,
            "reference_nav": config.reference_nav,
            "lookback": config.lookback_observations,
            "simulations": config.simulations,
            "seed": config.seed,
            "threshold": evt.threshold_quantile,
            "significance": config.significance,
            "minimum_previous_state": config.minimum_previous_state,
        }
        plot_backtests(forecasts, output)
        (output / "backtest_report.md").write_text(
            render_backtest_report(summary, latest, context), encoding="utf-8"
        )
        source_root = Path(__file__).resolve().parents[2]
        sources = sorted((source_root / "src").rglob("*.py")) + [source_root / "run_backtest.py"]
        write_json(
            output / "summary.json",
            dict(
                **context,
                config=settings,
                git=_git_state(source_root),
                weight_basis="fixed target exposures; one-session hypothetical P/L, no compounding or fees",
                exception_rule="realized signed loss strictly greater than forecast VaR; equality is no exception",
                review_record="docs/final/manual-backtest-check.md",
                evaluation_caveat="retrospective evaluation; final-period performance has previously been viewed",
                model_selection="none; all four prespecified methods reported separately by period",
                input_manifest_sha256=file_hash(snapshot / "manifest.json"),
                development_returns_sha256=sha256(
                    development.to_csv(float_format="%.17g").encode()
                ).hexdigest(),
                dependency_lock_sha256=file_hash(source_root / "uv.lock"),
                packages={
                    p: version(p)
                    for p in ("numpy", "pandas", "scipy", "exchange-calendars", "matplotlib")
                },
                code_sha256={str(p.relative_to(source_root)): file_hash(p) for p in sources},
                outputs_sha256={
                    p.name: file_hash(p)
                    for p in sorted(output.iterdir())
                    if p.suffix in {".csv", ".md", ".png"}
                },
            ),
        )
    except Exception as exc:
        write_json(
            output / "status.json",
            dict(status, status="failed", error=f"{type(exc).__name__}: {exc}"),
        )
        raise
    write_json(
        output / "status.json",
        dict(status, status="complete", human_validation="see manual worksheet"),
    )
    return output
