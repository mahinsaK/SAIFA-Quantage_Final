"""Auditable forecasts and statistical outcomes; missing evidence is explicit."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Forecast:
    strategy: str
    method: str
    confidence: float
    period: str
    window_start: str
    as_of: str
    forecast_date: str
    weights_as_of: str
    observations: int
    reference_nav: float
    horizon_sessions: int
    var_fraction: float | None
    es_fraction: float | None
    loss_fraction: float
    exception: bool | None
    status: str
    warning: str
    evt_threshold: float | None = None
    evt_exceedances: int | None = None
    evt_shape: float | None = None
    evt_scale: float | None = None
    mc_seed_date_ordinal: int | None = None


@dataclass(frozen=True)
class CoverageResult:
    observations: int
    valid_forecasts: int
    missing_forecasts: int
    exceptions: int
    expected_exceptions: float
    exception_rate: float | None
    statistic: float | None
    p_value: float | None
    exact_p_value: float | None
    decision: str
    warning: str


@dataclass(frozen=True)
class IndependenceResult:
    n00: int
    n01: int
    n10: int
    n11: int
    statistic: float | None
    p_value: float | None
    decision: str
    warning: str


@dataclass(frozen=True)
class TrafficLight:
    observations: int
    exceptions: int | None
    zone: str | None
    status: str
    warning: str
