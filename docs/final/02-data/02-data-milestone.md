# Data foundation milestone

Completed implementation and automated checks: 23 October 2026.

Snapshot: `20261023T102523Z-0d40a885`.

## Observed results

| Check | Result |
|---|---|
| ETF universe | SPY, EFA, EEM, AGG, GLD, XLE, XLK acquired from Yahoo via yfinance |
| Risk-free input | FRED DGS3MO, with explicit annual-percent units and lagged proxy accrual |
| Requested window | 2004-01-01 inclusive to 2026-10-23 exclusive |
| Common price window | 2004-11-18 to 2026-10-22 |
| Common price observations | 5,516 per ETF |
| Return window | 2004-11-19 to 2026-10-22 |
| Return observations | 5,515 per ETF |
| Leading unavailable history | GLD: 222 requested US sessions; excluded explicitly from the common window |
| Missing sessions after each series starts | Zero for all seven ETFs |
| Blocking quality flags | Zero |
| Large daily-return flags | 48 observations across ETFs; retained |
| Volatility-shift screening flags | 323 observations across ETFs; retained |
| Total review flags | 371; these are not 371 confirmed errors |
| ADF | All seven reject the unit-root null at 5% on the descriptive common sample; no claim of stable variance or distribution |
| Crisis date coverage | 2008, March 2020 and 2022 are covered; stress tests are not yet implemented |
| Unit/integration tests | 21 passed, offline, including missing prices, crisis-loss retention, adjustment-field requirements, lagged rates, snapshot corruption and failed acquisition/preparation |
| Static checks | Ruff passed |
| Frozen-data reproduction | All 10 derived output files byte-identical after a second offline build |

## Evidence

- [Raw manifest](../../../data/snapshots/20261023T102523Z-0d40a885/manifest.json): sources, settings, package versions and input hashes.
- [Summary](../../../output/data/20261023T102523Z-0d40a885/summary.json): dates, counts, source-code and output hashes.
- [Coverage](../../../output/data/20261023T102523Z-0d40a885/coverage.csv).
- [Quality report](../../../output/data/20261023T102523Z-0d40a885/quality_report.md).
- [Flag register](../../../output/data/20261023T102523Z-0d40a885/quality_flags.csv).
- [Stationarity results](../../../output/data/20261023T102523Z-0d40a885/stationarity.csv).
- [Implementation and commands](01-data-methodology.md).
- [Executable tests](../../../tests/test_data_foundation.py).

The first live run exposed a calendar-boundary bug when the requested start date was a holiday. It was corrected by selecting actual sessions within the requested bounds and adding a regression test. No data was redownloaded or manually edited to resolve it.

## What remains

The data requirements have implementation evidence, but final human sign-off remains pending. Team members should inspect the retained flags and source action fields, explain the missingness/calendar policy, check the risk-free approximation, and record actual review evidence in a separate log. No human validation or final data-error classification is invented here.

The snapshot captures currently available historical data, not historical publication vintages. The risk-free date lag does not establish exact historical availability times. Full-sample ADF and quality summaries are descriptive; choose and freeze training/validation/test windows before using them for model decisions.

Portfolio accounting and the 40% SPY / 60% AGG benchmark are the next implementation milestone. No portfolio returns, allocation optimisation, CAPM, VaR/ES/EVT forecasts, formal risk backtests or Streamlit app are included in this completed data milestone.
