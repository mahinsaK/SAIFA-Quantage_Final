# Observed CPI real-growth review — 28 October 2026

Status: **automated calculation and artifact checks complete; independent human review pending**. This worksheet does not approve an allocation or the proposed 3% objective.

## Data and timing to check

The original frozen market snapshot is `20261023T102523Z-0d40a885`. A separate committed [CPI overlay](../../../data/inflation/README.md) holds FRED `CPIAUCSL`, monthly and seasonally adjusted, retrieved 28 October 2026. The portfolio risk as-of is 22 October 2026. FRED lists the latest September 2026 CPI observation as released 14 October 2026. The comparison ends on **30 September 2026**, the last portfolio session in that CPI month, and begins with the **3 January 2022** funded NAV. It uses January 2022 CPI as a retrospective monthly approximation for the starting purchasing power.

The 2025-10 CPI value is missing in FRED's CSV. [BLS explains the data-collection interruption](https://www.bls.gov/cpi/additional-resources/2025-federal-government-shutdown-impact-cpi.htm). It is kept missing and not interpolated. The endpoint comparison does not need that intermediate value; it does not supply a complete monthly real-NAV path. FRED series revisions and the monthly-to-daily date approximation remain limitations.

## Independent hand calculation

```text
January 2022 CPI = 282.543
September 2026 CPI = 336.298
Price-level factor = 336.298 / 282.543 = 1.19025422679
Real ending wealth = costed nominal NAV on 2026-09-30 / price-level factor
Annualised real growth = (real ending wealth / 10,000,000) ^ (365.25 / 1731 days) - 1
```

Check the elapsed day count against the two dates, then calculate one row independently before using the generated CSV. The USD 10 million denominator includes the opening trading cost. These are **before-withdrawal** figures; the 3% objective in the draft policy is also before withdrawals.

| Candidate | Nominal NAV at Sep 30 | Real ending wealth | Observed real growth / year | 3% test in observed period |
|---|---:|---:|---:|---|
| 40/60 baseline | see `observed_real.csv` | USD 10,325,533.13 | 0.6782% | Below |
| Minimum volatility | see `observed_real.csv` | USD 11,263,181.62 | 2.5418% | Below |
| Maximum Sharpe | see `observed_real.csv` | USD 11,352,773.00 | 2.7133% | Below |

Verify the exact nominal values, deflator, dates, and annualisation in `output/decision/<snapshot>/observed_real.csv`. The final October 22 nominal portfolio values in the performance table are a different end date and must not be paired with September CPI. All three observed rates are below 3% in this **under-five-year** sample; this does not prove the proposed ten-year objective will fail in the future.

The existing 0%, 2% and 4% withdrawal scenarios still use assumed inflation and a hypothetical payment schedule. They are not recalculated with CPI or presented as observed university spending. Actual client payments, taxes and management fees remain unknown.

## Reviewer record — complete only after checking

- Reviewer name/date:
- CPI source, latest-release timing and October 2025 missing row checked:
- Starting/ending CPI and dates matched:
- Independent deflator, real USD and annualised growth calculation:
- App, CSV, report and tear sheet figures matched:
- Explanation of observed period versus ten-year objective:
- Explanation of observed CPI versus hypothetical spending inflation:
- Discrepancies/corrections:
- Sign-off scope and initials:
