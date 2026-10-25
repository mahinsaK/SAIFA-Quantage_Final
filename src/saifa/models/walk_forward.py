"""Date-aligned rolling risk forecasts for frozen target exposures."""

from collections.abc import Callable
from dataclasses import asdict

import exchange_calendars as xcals
import numpy as np
import pandas as pd

from saifa.domain.backtesting import Forecast
from saifa.domain.config import BacktestConfig, EVTConfig
from saifa.domain.risk import TailEstimate
from saifa.models.evt import fit_pot, pot_tail
from saifa.models.risk import empirical_tail, fit_gaussian, normal_tail, ordered_weights


def forecast_positions(returns: pd.DataFrame, config: BacktestConfig) -> np.ndarray:
    index = returns.index
    if (
        not isinstance(index, pd.DatetimeIndex)
        or returns.empty
        or index.tz is not None
        or not index.is_unique
        or not index.is_monotonic_increasing
        or not index.equals(index.normalize())
    ):
        raise ValueError("Returns require unique ordered naive session dates")
    end = pd.Timestamp(config.end_exclusive) - pd.Timedelta(days=1)
    calendar = xcals.get_calendar("XNYS", start=config.start, end=end)
    targets = calendar.sessions.tz_localize(None)
    if targets.empty or not targets.isin(index).all():
        raise ValueError("Requested forecast range is empty or has missing observed sessions")
    positions = index.get_indexer(targets)
    if positions[0] < config.lookback_observations:
        raise ValueError("Insufficient pre-forecast training history; no shorter fallback")
    span = index[positions[0] - config.lookback_observations : positions[-1] + 1]
    expected = xcals.get_calendar("XNYS", start=span[0], end=span[-1]).sessions.tz_localize(None)
    if not span.equals(expected):
        raise ValueError("Training/forecast span must contain consecutive XNYS sessions")
    fit_gaussian(returns.loc[span])
    return positions


def standardized_mc_tails(
    forecast_date: pd.Timestamp, config: BacktestConfig
) -> dict[float, TailEstimate]:
    # Stable by target date: changing start date or portfolio order cannot change a forecast's draws.
    seed = np.random.SeedSequence([config.seed, forecast_date.date().toordinal()])
    draws = np.random.Generator(np.random.PCG64(seed)).standard_normal(config.simulations)
    ordered = np.sort(draws)
    # Exact same inverse empirical CDF and fractional-tail ES as empirical_tail, sorting once.
    tails = {}
    for confidence in config.confidence_levels:
        var = float(np.quantile(ordered, confidence, method="inverted_cdf"))
        mass = np.clip(np.arange(1, len(ordered) + 1) - confidence * len(ordered), 0, 1)
        tails[confidence] = TailEstimate(var, float(ordered @ mass / mass.sum()))
    return tails


def walk_forward(
    returns: pd.DataFrame,
    portfolios: dict[str, pd.Series],
    config: BacktestConfig,
    evt: EVTConfig,
    weights_as_of: str,
    validation_end_exclusive: str,
    progress: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    positions = forecast_positions(returns, config)
    if not portfolios:
        raise ValueError("At least one portfolio is required")
    weight_date = pd.Timestamp(weights_as_of)
    if weight_date > returns.index[positions[0] - 1]:
        raise ValueError("Portfolio weights use information after the first forecast origin")
    weights = {name: ordered_weights(w, returns.columns) for name, w in portfolios.items()}
    # Projection preserves covariance: sample variance of R@w equals w'Cov(R)w.
    projected = {
        name: returns.iloc[: positions[-1] + 1].to_numpy() @ w for name, w in weights.items()
    }
    records = []
    for step, position in enumerate(positions):
        date = returns.index[position]
        as_of = returns.index[position - 1]
        first = position - config.lookback_observations
        mc = standardized_mc_tails(date, config)
        for strategy, series in projected.items():
            history = series[first:position]  # Excludes target date and all future returns.
            loss = float(-series[position])
            mean, sigma = float(history.mean()), float(history.std(ddof=1))
            fitted = fit_pot(-history, evt.threshold_quantile, evt.minimum_exceedances)
            for confidence in config.confidence_levels:
                evt_tail = pot_tail(fitted, confidence)
                gaussian_mc = TailEstimate(
                    -mean + sigma * mc[confidence].var_fraction,
                    -mean + sigma * mc[confidence].es_fraction,
                )
                for method, tail, status, warning in (
                    (
                        "historical",
                        empirical_tail(-history, confidence),
                        "ok",
                        "Empirical tail; limited extremes",
                    ),
                    (
                        "parametric_normal",
                        normal_tail(mean, sigma, confidence),
                        "ok",
                        "Normal distribution assumption",
                    ),
                    (
                        "monte_carlo_normal",
                        gaussian_mc,
                        "ok",
                        "Projected Normal simulation; finite Monte Carlo error",
                    ),
                    ("evt_pot_gpd", evt_tail, evt_tail.status, evt_tail.warning),
                ):
                    var, es = tail.var_fraction, tail.es_fraction
                    if var is not None and not np.isfinite(var):
                        raise ValueError("Nonfinite VaR must be represented as unavailable")
                    record = Forecast(
                        strategy=strategy,
                        method=method,
                        confidence=confidence,
                        period="validation"
                        if date < pd.Timestamp(validation_end_exclusive)
                        else "evaluation",
                        window_start=str(returns.index[first].date()),
                        as_of=str(as_of.date()),
                        forecast_date=str(date.date()),
                        weights_as_of=str(weight_date.date()),
                        observations=len(history),
                        reference_nav=config.reference_nav,
                        horizon_sessions=1,
                        var_fraction=var,
                        es_fraction=es,
                        loss_fraction=loss,
                        exception=bool(loss > var) if var is not None else None,
                        status=status,
                        warning=warning,
                        evt_threshold=fitted.threshold if method == "evt_pot_gpd" else None,
                        evt_exceedances=fitted.exceedances if method == "evt_pot_gpd" else None,
                        evt_shape=fitted.shape if method == "evt_pot_gpd" else None,
                        evt_scale=fitted.scale if method == "evt_pot_gpd" else None,
                        mc_seed_date_ordinal=date.date().toordinal()
                        if method == "monte_carlo_normal"
                        else None,
                    )
                    records.append(asdict(record))
        if progress and (step % 100 == 0 or step == len(positions) - 1):
            progress(step + 1, len(positions))
    frame = pd.DataFrame(records)
    frame["exception"] = frame["exception"].map({True: 1.0, False: 0.0})
    for measure in ("var", "es", "loss"):
        frame[f"{measure}_percent"] = pd.to_numeric(frame[f"{measure}_fraction"]) * 100
        frame[f"{measure}_usd"] = pd.to_numeric(frame[f"{measure}_fraction"]) * config.reference_nav
    return frame
