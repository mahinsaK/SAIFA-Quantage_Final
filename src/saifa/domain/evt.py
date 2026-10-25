"""Explicit success, unsupported tails and uncertainty for peaks-over-threshold fits."""

from dataclasses import dataclass


@dataclass(frozen=True)
class POTFit:
    quantile: float
    threshold: float
    observations: int
    exceedances: int
    mean_excess: float | None
    shape: float | None
    scale: float | None
    modified_scale: float | None
    status: str
    warning: str


@dataclass(frozen=True)
class POTEstimate:
    confidence: float
    var_fraction: float | None
    es_fraction: float | None
    status: str
    warning: str
