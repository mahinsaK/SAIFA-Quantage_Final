# Data quality human review worksheet

Status: **human review pending**.

Snapshot: `20261023T102523Z-0d40a885`.

The automated pipeline found zero blocking errors and 371 review flags: 48 large daily returns and 323 volatility-shift candidates. These flags were retained because they may represent real market stress. A high count of overlapping volatility-window flags does not mean there are 371 independent errors.

| Ticker | Large returns | Volatility candidates | Total |
|---|---:|---:|---:|
| SPY | 4 | 98 | 102 |
| EFA | 6 | 65 | 71 |
| EEM | 13 | 35 | 48 |
| AGG | 0 | 40 | 40 |
| GLD | 2 | 31 | 33 |
| XLE | 17 | 22 | 39 |
| XLK | 6 | 32 | 38 |
| **Total** | **48** | **323** | **371** |

## Review procedure

1. Open `output/data/20261023T102523Z-0d40a885/quality_flags.csv`.
2. Group by ticker, flag type and nearby dates rather than treating each rolling-window row as independent.
3. Check at minimum the 2008 crisis cluster, March 2020 cluster, 2022 rate-shock period and every `large_daily_return` row.
4. Compare adjusted close with raw close/dividend/split fields in the frozen snapshot. Do not edit the CSV data manually.
5. Record whether each inspected cluster is a plausible market event, a corporate adjustment requiring explanation, or a suspected provider error requiring a fresh snapshot/investigation.
6. Confirm that zero missing session prices were silently filled and that GLD's unavailable leading history was excluded.

## Human review record

- Reviewer name:
- Review date:
- Rows/clusters inspected:
- External or frozen-source evidence used:
- Large-return conclusion:
- Volatility-cluster conclusion:
- Adjustment-factor conclusion:
- Missingness/calendar conclusion:
- Corrections or follow-up required:
- Reviewer initials/sign-off:

Do not change this status to complete until a team member performs and records the review. AI-generated grouping can assist inspection but cannot supply the human sign-off required by the brief.
