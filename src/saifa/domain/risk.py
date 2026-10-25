"""Typed distribution inputs and one-day loss estimates."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class TailEstimate:
    var_fraction: float
    es_fraction: float


@dataclass(frozen=True)
class GaussianFit:
    mean: pd.Series
    covariance: pd.DataFrame
    observations: int


@dataclass(frozen=True)
class RiskEstimate:
    strategy: str
    method: str
    confidence: float
    horizon_sessions: int
    reference_nav: float
    observations: int
    var_fraction: float
    es_fraction: float
    var_percent: float
    es_percent: float
    var_usd: float
    es_usd: float
    scenarios: int | None
    seed: int | None
    effective_tail_observations: float | None
    mc_var_standard_error: float | None
    mc_es_standard_error: float | None
    warning: str
