# Manual EVT check and threshold review

Status: **human review pending**. Calculate independently, then compare. Do not copy a sign-off from another worksheet.

## A. Count and loss convention

A portfolio has 1,000 one-day loss observations. Its empirical 90th-percentile loss threshold is 2% (`u=0.02`), with 100 strict exceedances.

```text
p_u = 100 / 1000 = 0.10
Threshold CDF = 1 - 0.10 = 0.90
At 99% confidence, p_u / (1-c) = 0.10 / 0.01 = 10
```

An observed 3% loss has excess `0.03-0.02=0.01` (one percentage point). A 2% loss is at the threshold and is not a strict exceedance. If ties reduce the count to 50, use `p_u=0.05`, not 0.10. Then 95% confidence is at the boundary and this implementation does not provide a tail extrapolation there.

## B. GPD calculation

Assume `xi=0.2`, `beta=0.01`, `u=0.02`, `p_u=0.10`, `c=0.99`, NAV USD 10m. These are artificial parameters, not fitted fund values.

```text
10^0.2 = 1.58489319246
VaR = 0.02 + (0.01/0.2)*(1.58489319246-1)
    = 0.049244659623 = 4.9244659623% = USD 492,446.60
ES  = (0.049244659623 + 0.01 - 0.2*0.02)/(1-0.2)
    = 0.069055824529 = 6.9055824529% = USD 690,558.25
```

Tolerance: USD 0.10 using enough calculator precision. Both are one-session losses; do not annualise them.

## C. Exponential and unavailable cases

Keep the inputs above but set `xi=0`. The division-by-xi formula must be replaced by its limit:

```text
VaR = 0.02 + 0.01*ln(10) = 0.043025850930
    = 4.3025850930% = USD 430,258.51
ES  = VaR + 0.01 = 0.053025850930
    = 5.3025850930% = USD 530,258.51
```

Explain why the code must show unavailable ES when `xi >= 1`: the fitted GPD tail has no finite mean. This is not zero risk. With 1,000 distinct observations, a 97.5% threshold has only 25 exceedances, below the default minimum 50; that fit is also withheld. A 90% threshold is not a valid default EVT fit for 90% forecast confidence.

## D. Reproduce and inspect the actual run

```bash
uv run --locked python run_evt.py
uv run --locked pytest tests/test_evt.py -q
uv run --locked pytest -q
uv run --locked ruff check .
```

Open the printed `evt_report.md`. Confirm:

1. Six selected EVT estimates and 24 four-method comparison rows at default settings; same dates, holdings, horizon and USD 10m basis.
2. Threshold diagnostics have 36 rows (three allocations × two periods × six thresholds), and sensitivity has 72 rows at two confidences. Blank values have explicit reasons.
3. Check one selected VaR and ES USD conversion from `evt_estimates.csv` using full precision. The report rounds displayed numbers.
4. Development diagnostics end before 2019-01-01. Current-window diagnostics do not change the selected quantile. Record which development plots you inspected.
5. For 85%, 90%, 92.5% thresholds compare count, shape, modified scale, Q-Q deviations and 99% ES. Explain the trade-off; do not just say "90% is best". If the evidence is weak, record that and request further investigation.
6. Open `bootstrap_draws.csv`: each allocation has 200 replicates per confidence. Read valid counts and interval warnings. The interval describes uncertainty in the estimate, not the range in which 95% of future losses must fall.
7. Rerun unchanged settings and check numerical results agree. You do not need to calculate hundreds of model fits by hand.

## Reviewer record

- Reviewer name:
- Review date:
- Calculator/spreadsheet/paper used:
- Part A count and sign matched:
- Part B VaR and ES matched within USD 0.10:
- Part C exponential calculation and unavailable cases understood:
- Part D output and USD checks performed:
- Snapshot and exact run folder reviewed:
- Commands actually run and their results:
- Discrepancies and corrections:
- In your own words: What is the difference between threshold percentile and VaR confidence?
- In your own words: Why can raising the threshold make the estimate less reliable?
- Development plots and sensitivity values inspected:
- Threshold decision (retain 90% candidate / investigate further) and evidence:
- In your own words: What does a bootstrap interval tell us, and what does it not tell us?
- Reviewer initials/sign-off:

Only record checks actually completed. A human may complete the arithmetic while leaving threshold approval pending; state both separately. Mathematical checks do not prove forecasting quality or suitability for the endowment.
