"""Typed spending results and explicit research assumptions."""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SpendingResult:
    daily: pd.DataFrame
    payments: pd.DataFrame
    summary: dict


INFLATION_SCENARIOS = (0.0, 0.02, 0.04)
WITHDRAWAL_RATE = 0.03
REAL_CAPITAL_OBJECTIVE = 0.03
CPI_LIMITATION = (
    "Observed historical real growth now uses a separate frozen FRED CPIAUCSL monthly series "
    "through September 2026; the original market snapshot remains unchanged. The CPI series "
    "was released by 22 October 2026, but its monthly average is only an approximation to "
    "purchasing power on individual trading days and may later be revised. October 2025 CPI is "
    "missing in the source; no value is interpolated for that month. The 0%, 2% and 4% "
    "spending rates remain illustrative inflation assumptions, not observed CPI or client instructions. "
    "A shorter historical period cannot establish the proposed ten-year objective."
)
DECISION = (
    "Defer implementation under the current proposed mandate. Retain minimum volatility as "
    "a conditional research candidate for committee discussion, not an approved allocation. "
    "Its lower development variance fits the preservation priority, but all three candidates "
    "breach the proposed crisis drawdown review level and spending suitability is unresolved."
)
CONDITIONS = (
    "Confirm actual spending amounts, dates, currency, taxes, fees and liquidity needs.",
    (
        "Review the CPI benchmark, its monthly timing and the observed real-growth shortfall; "
        "confirm the client's actual ten-year objective."
    ),
    (
        "Agree an explicit response to crisis drawdown and severe hypothetical-shock breaches; "
        "do not raise limits merely to pass observed tests."
    ),
    "Review failed coverage/clustering tests, sparse tail evidence and independent model validation.",
    (
        "Team independently evaluates this AI-assisted recommendation, approves the scenario, "
        "completes review records and obtains committee policy approval before implementation."
    ),
)
