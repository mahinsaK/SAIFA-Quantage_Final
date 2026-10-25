"""Typed loss attribution and stress outcomes."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AssetContribution:
    ticker: str
    weight: float
    marginal_fraction: float | None
    component_fraction: float | None
    share_percent: float | None


@dataclass(frozen=True)
class ContributionResult:
    method: str
    measure: str
    confidence: float
    total_fraction: float
    assets: tuple[AssetContribution, ...]
    status: str
    warning: str
    effective_tail_observations: float | None = None


@dataclass(frozen=True)
class HistoricalStressResult:
    strategy: str
    scenario: str
    requested_start: str
    requested_end_exclusive: str
    expected_sessions: int
    observed_sessions: int
    status: str
    warning: str
    reference_nav: float
    weights_as_of: str
    base_date: str | None = None
    last_date: str | None = None
    weights_available_at_start: bool | None = None
    terminal_return_fraction: float | None = None
    terminal_loss_fraction: float | None = None
    terminal_loss_usd: float | None = None
    worst_day_loss_fraction: float | None = None
    worst_loss_from_initial_usd: float | None = None
    maximum_drawdown_fraction: float | None = None
    drawdown_usd_at_max_fraction: float | None = None
    peak_date: str | None = None
    trough_date: str | None = None
    peak_nav: float | None = None
    trough_nav: float | None = None
    drawdown_review_level: float | None = None
    review_trigger_breached: bool | None = None


@dataclass(frozen=True)
class StressRun:
    summary: HistoricalStressResult
    path: pd.DataFrame
    components: pd.DataFrame


@dataclass(frozen=True)
class ShockResult:
    strategy: str
    scenario: str
    multiplier: float
    horizon_sessions: int
    reference_nav: float
    loss_fraction: float
    loss_usd: float
    review_level: float
    review_trigger_breached: bool


@dataclass(frozen=True)
class ShockRun:
    summary: ShockResult
    components: pd.DataFrame
