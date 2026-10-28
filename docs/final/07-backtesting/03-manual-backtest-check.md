# Manual walk-forward backtest check

Status: **Parts A–D calculations and interpretation recorded; Part E selected forecast, evaluation summary and latest Basel rows checked by the reviewer; chart and warning review pending**. Model calibration and final portfolio suitability remain under review.

## A. Timing, units and exceptions

A forecast issued at the 31 December 2018 close predicts the next exchange session, 2 January 2019. Its training window must end on 31 December; neither the 2 January return nor later returns may enter it.

For USD 10m and forecast VaR `0.012` (1.2%), calculate the USD VaR and classify these next-session returns:

| Portfolio return | Signed loss | Loss USD | Exception? |
|---:|---:|---:|---|
| -1.5% | 1.5% | 150,000 | Yes: exceeds 120,000 VaR |
| -1.2% | 1.2% | 120,000 | No: equality |
| +0.5% | -0.5% | -50,000 | No: a gain |

These are independent one-session examples with the same reference NAV, not a three-day compounded investment path.

## B. Kupiec by hand

Assume 250 sessions, 99% confidence and five exceptions. Use natural logarithms:

```text
p = 1 - 0.99 = 0.01
q = 5 / 250 = 0.02
Expected exceptions = 250 × 0.01 = 2.5
LRuc = 2 × [245 × ln(0.98/0.99) + 5 × ln(0.02/0.01)]
     = 1.95680978823
```

Calculate the statistic yourself; tolerance 0.000001. Using a chi-square survival function with one degree of freedom gives `p ≈ 0.1618549172`. In a spreadsheet, `CHISQ.DIST.RT(1.95680978823,1)` gives that tail probability. At 5%, the decision is **do not reject**, not proof that the model is correct. The supplemental exact two-sided binomial p-value is approximately `0.1078123731`; you need not calculate its full sum by hand.

## C. Christoffersen transitions by hand

Write this 20-session exception sequence and count adjacent pairs, including the transition between the two repeated blocks:

```text
0 0 1 0 1 1 0 0 0 1  0 0 1 0 1 1 0 0 0 1
```

Expected counts: `n00=6`, `n01=6`, `n10=5`, `n11=2`, totalling 19 transitions.

```text
pi01 = 6/12 = 0.5
pi11 = 2/7
pi   = 8/19
log L0 = 11 ln(11/19) + 8 ln(8/19)
log L1 = 12 ln(0.5) + 5 ln(5/7) + 2 ln(2/7)
LRind = 2 × (log L1 - log L0) = 0.852613966251
chi-square(1) tail probability ≈ 0.3558139097
```

Tolerance for the statistic: 0.000001. The decision is do not reject, with a sparse-cell warning. This small artificial sequence checks arithmetic; it is weak evidence about forecasting quality. A sequence of 250 zero exceptions yields insufficient transitions from previous state 1, so independence must be **unavailable**, not passed. If a forecast is missing, do not remove its date and connect its neighbours.

## D. Traffic-light boundaries

At 99% confidence with exactly 250 complete sessions, verify: four exceptions = green, five = yellow, nine = yellow, ten = red. A 249-session window has no colour. A 95% confidence forecast does not use these thresholds. Five exceptions in Part B is yellow even though Kupiec does not reject: the decision rules have different purposes.

## E. Check the actual frozen run

```bash
uv run --locked python commands/run_backtest.py
uv run --locked pytest tests/test_backtesting.py -q
uv run --locked pytest -q
uv run --locked ruff check .
```

Open the output folder printed by the runner. The current default is `output/backtest/20261023T102523Z-0d40a885/93efaf13a75a/`.

1. Confirm `status.json` says `complete`, and `summary.json` matches the snapshot and configuration reviewed.
2. Confirm 1,963 forecast sessions and 47,112 rows: three portfolios × four methods × two confidences × 1,963. Validation contains 757 sessions; evaluation contains 1,206. Confirm missing counts rather than assuming all fits succeeded.
3. In `forecasts.csv`, select one baseline row. Check `as_of < forecast_date`, 1,000 training observations, `weights_as_of=2018-12-31`, percent = fraction × 100, USD = fraction × 10m, and the strict exception rule. Use full CSV precision when comparing with VaR.
4. For baseline Historical 99% evaluation, verify 11 exceptions out of 1,206, expected count 12.06, Kupiec p approximately 0.7555 and independence p approximately 0.002892. Explain how an acceptable total count can still hide clusters of exceptions.
5. Inspect the baseline evaluation chart, especially consecutive red points. Read the warning columns in `test_summary.csv`; do not interpret a non-rejection as guaranteed safety.
6. In `basel_latest.csv`, baseline Historical evaluation has one exception (green), while minimum-volatility Historical has six (yellow) over 24 October 2025–22 October 2026. Compare the same period/model/confidence. Read `basel_rolling.csv` for earlier windows rather than judging the whole history from the final colour.
7. Explain why this risk backtest uses fixed target exposures and USD 10m, while the earlier performance comparison has changing NAV and monthly rebalancing costs. These are different questions and should not be presented as the same loss series.

## Reviewer record — complete after checking

- Reviewer name: Mahinsa Kuruppu
- Review date: 25 Oct 2026
- Calculator/spreadsheet/paper used: Calculator
- Part A timing, USD values and exception flags matched:
  VaR = $120,000. Exceptions: Yes, No, No. Training data must exclude future returns.

- Part B calculated LRuc and interpretation:
  LRuc = 1.956810, p = 0.161855. Do not reject at 5%.

- Part C transition counts and calculated LRind:
  n00=6, n01=6, n10=5, n11=2. LRind = 0.852614, p = 0.355814. Do not reject.

- Part D boundary and unavailable cases understood:
  4 = Green, 5–9 = Yellow, 10+ = Red. Incomplete windows and insufficient transitions are unavailable.

- Part E exact snapshot/run folder and selected forecast row:
  output/backtest/20261023T102523Z-0d40a885/93efaf13a75a/. On 29 Oct 2026, the reviewer reported that the selected baseline Historical 99% evaluation row for 2022-01-03 matched: as-of 2021-12-31, 1,000 observations, VaR USD 145,367.77, realised loss USD 17,863.01 and exception 0. The reviewer also reported that the evaluation summary matched 11 exceptions in 1,206 sessions, Kupiec p 0.7555 and independence p 0.002892; the latest 250-session Basel rows matched baseline 1/green and minimum volatility 6/yellow. This records the reported row comparison, not full Part E sign-off.

- Commands actually run and observed results:
Forecast sessions: 1/1963
Forecast sessions: 101/1963
Forecast sessions: 201/1963
Forecast sessions: 301/1963
Forecast sessions: 401/1963
Forecast sessions: 501/1963
Forecast sessions: 601/1963
Forecast sessions: 701/1963
Forecast sessions: 801/1963
Forecast sessions: 901/1963
Forecast sessions: 1001/1963
Forecast sessions: 1101/1963
Forecast sessions: 1201/1963
Forecast sessions: 1301/1963
Forecast sessions: 1401/1963
Forecast sessions: 1501/1963
Forecast sessions: 1601/1963
Forecast sessions: 1701/1963
Forecast sessions: 1801/1963
Forecast sessions: 1901/1963
Forecast sessions: 1963/1963
Backtest outputs: /Users/mahinsak/SAIFA/output/backtest/20261023T102523Z-0d40a885/93efaf13a75a
Read backtest_report.md and docs/final/07-backtesting/03-manual-backtest-check.md.
..............................                                                     [100%]
30 passed in 6.53s
.................................................................................. [ 54%]
.....................................................................              [100%]
151 passed in 12.55s
All checks passed!

- Plots/table rows inspected:
  Reviewer reported matching selected forecast, test-summary and latest-Basel rows on 29 Oct 2026. Evaluation chart and warning-column inspection still need explicit confirmation.

- Discrepancies and corrections:
  No arithmetic discrepancies identified in Parts A–D or the reviewer-confirmed Part E rows. The chart and warning review remains open.

- In your own words:
Why can correct overall exception frequency coexist with dangerous clustering?
The total number of VaR exceptions can be close to the expected number even if several happen on nearby days. In our baseline Historical 99% evaluation, 11 exceptions occurred versus 12.06 expected, but the independence test found evidence of clustering. Consecutive large losses can be especially difficult for an endowment that needs to preserve capital.

- In your own words:
Why is a green latest window or p-value above 0.05 not proof that the model is safe?
A green result describes only that 250-day window. A p-value above 0.05 means the test did not find enough evidence to reject its assumption; it does not prove the assumption is true or guarantee future forecasts. Other periods and tests can reveal problems.

- In your own words:
Why must tomorrow's return be excluded from today's forecast?
Tomorrow's return is unknown when today's forecast is made. Using it would give the model future information and make the backtest look more accurate than a forecast that could actually have been made.

- Interpretation decision and limitations to carry into stress analysis:
I accept the checked calculations as a record of how the backtest behaved, but I do not treat any VaR model as proven safe. I will retain the coverage and clustering warnings, compare them with the historical and hypothetical stress losses, and discuss the drawdown review-level breaches before recommending an allocation.

- Reviewer initials/sign-off (Parts A–D): KAD

Keep human arithmetic completion separate from model approval. It is valid to confirm the implementation's calculations while recording concerns about the model's forecasting performance.
