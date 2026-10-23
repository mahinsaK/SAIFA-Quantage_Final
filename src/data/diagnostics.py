"""Descriptive diagnostics, not model-selection or final-validation evidence."""

import warnings

import pandas as pd
from statsmodels.tsa.stattools import adfuller


def stationarity_table(log_returns: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker, series in log_returns.items():
        row = {
            "ticker": ticker,
            "input_observations": len(series),
            "regression": "constant",
            "autolag": "AIC",
            "significance": 0.05,
            "scope": "full-sample descriptive only; repeat within training windows",
        }
        if len(series) < 100 or series.nunique() < 2:
            row.update(status="not_estimable", interpretation="Too few or constant returns")
        else:
            with warnings.catch_warnings(record=True) as recorded:
                warnings.simplefilter("always")
                statistic, pvalue, lags, observations, critical, _ = adfuller(
                    series.to_numpy(), regression="c", autolag="AIC"
                )
            row.update(
                status="estimated",
                statistic=statistic,
                p_value=pvalue,
                used_lag=lags,
                regression_observations=observations,
                critical_5_percent=critical["5%"],
                interpretation=(
                    "Reject unit-root null at 5%; not proof of stable variance/distribution"
                    if pvalue < 0.05
                    else "Fail to reject unit-root null at 5%"
                ),
                warnings="; ".join(str(w.message) for w in recorded),
            )
        rows.append(row)
    return pd.DataFrame(rows)
