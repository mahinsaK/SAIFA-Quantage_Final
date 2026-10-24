# Manual walk-forward backtest check

Status: **pending actual human calculations and interpretation**. Expected answers below are reference values, not a completed reviewer record. Use a calculator/paper or a spreadsheet and record only checks actually performed. You do not need to calculate thousands of forecasts manually.

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
uv run --locked python run_backtest.py
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

- Reviewer name:
- Review date:
- Calculator/spreadsheet/paper used:
- Part A timing, USD values and exception flags matched:
- Part B calculated LRuc and interpretation:
- Part C transition counts and calculated LRind:
- Part D boundary and unavailable cases understood:
- Part E exact snapshot/run folder and selected forecast row:
- Commands actually run and observed results:
- Plots/table rows inspected:
- Discrepancies and corrections:
- In your own words: Why can correct overall exception frequency coexist with dangerous clustering?
- In your own words: Why is a green latest window or p-value above 0.05 not proof that the model is safe?
- In your own words: Why must tomorrow's return be excluded from today's forecast?
- Interpretation decision and limitations to carry into stress analysis:
- Reviewer initials/sign-off:

Keep human arithmetic completion separate from model approval. It is valid to confirm the implementation's calculations while recording concerns about the model's forecasting performance.
