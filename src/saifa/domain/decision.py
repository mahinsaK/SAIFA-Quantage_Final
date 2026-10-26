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
    "Observed inflation-adjusted wealth and actual real-growth attainment are unavailable: "
    "the frozen FRED input contains DGS3MO only, with no CPI series. "
    "The 0%, 2% and 4% rates are illustrative constant-inflation assumptions, not observations, "
    "forecasts or client instructions."
)
DECISION = (
    "Defer implementation under the current proposed mandate. Retain minimum volatility as "
    "a conditional research candidate for committee discussion, not an approved allocation. "
    "Its lower development variance fits the preservation priority, but all three candidates "
    "breach the proposed crisis drawdown review level and spending suitability is unresolved."
)
CONDITIONS = (
    "Confirm actual spending amounts, dates, currency, taxes, fees and liquidity needs.",
    "Obtain a documented inflation series and assess real wealth against the approved objective.",
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
