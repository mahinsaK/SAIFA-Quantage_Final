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
    "We recommend rejecting immediate implementation of the three tested allocations under "
    "our current proposed policy. Minimum volatility remains a conditional research candidate. "
    "Further consideration requires clarified client needs, additional model validation and "
    "an agreed response to the observed risk breaches."
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
        "Record independent checks of the team-provided recommendation, review and approve the "
        "hypothetical scenario, complete reviewer records and obtain client/committee policy "
        "approval before implementation."
    ),
)
