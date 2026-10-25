# Manual contributions and stress check

Status: **pending actual human calculation, scenario review and sign-off**. Expected answers below are reference values, not a completed reviewer record. Work through the examples with a calculator or spreadsheet, then fill the record in your own words.

## A. Normal contributions

Use weights A=0.4, B=0.6; daily means 0.001 and 0.0002; daily standard deviations 0.02 and 0.01; zero covariance. At 95%, use z=1.64485362695147 and phi(z)/(1-c)=2.06271280750743.

1. Calculate portfolio mean: `0.4×0.001 + 0.6×0.0002 = 0.00052`.
2. Calculate volatility: `sqrt(0.4²×0.02² + 0.6²×0.01²) = 0.01`.
3. VaR = `-0.00052 + 1.64485362695147×0.01 = 0.0159285362695147`.
4. Marginal A = `-0.001 + z×(0.02²×0.4)/0.01`; component A = `0.4×Marginal A = 0.0101270632124894`.
5. Marginal B = `-0.0002 + z×(0.01²×0.6)/0.01`; component B = `0.0058014730570253`.
6. Confirm components sum to VaR. At USD 10m, components are approximately USD 101,270.63 and USD 58,014.73, totaling USD 159,285.36.
7. Replace z by 2.06271280750743 and confirm total ES = `0.0201071280750743`, approximately USD 201,071.28.

Use tolerance 0.00000001 in fractions or USD 0.02 after rounding. The mean terms must not be omitted. A one-percentage-point increase in A funded by B uses `0.01×(Marginal A - Marginal B)`, not just A's marginal.

## B. Historical ES with ties

These are asset **losses**, not returns. Set both weights to 0.5 and confidence to 50% for easy arithmetic:

| Observation | A loss | B loss | Portfolio loss |
|---|---:|---:|---:|
| 1 | 0.04 | 0.00 | 0.02 |
| 2 | 0.02 | 0.02 | 0.02 |
| 3 | 0.03 | 0.01 | 0.02 |
| 4 | 0.00 | 0.00 | 0.00 |

Tail mass = `4×(1-0.5)=2`. Three observations tie at the boundary. Share the two units of tail mass equally: after normalization each tied observation has probability 1/3. Marginal A = 0.03; marginal B = 0.01. Components = 0.015 and 0.005; ES=0.02. Explain why arbitrarily selecting two tied observations could change the allocation even though total ES stays the same. This symmetric allocation is a selected subgradient, not always a unique derivative.

## C. Stress paths and drawdown

Start with USD 1,000, half in each asset. Day 1: A -20%, B 0%. Day 2: A +25%, B 0%.

- Asset holdings: (500,500) → (400,500) → (500,500).
- Portfolio NAV: 1,000 → 900 → 1,000.
- After day 1, A's weight is 400/900, not 50%.
- Terminal loss is zero; maximum drawdown is 10% and USD 100.

Second example: both assets gain 10%, then lose 20%. NAV = 1,000 → 1,100 → 880. Terminal loss is USD 120 (12% of initial capital), while maximum drawdown is 20% of the peak 1,100 = USD 220. Explain why calculating drawdown dollars as 20%×1,000 would be wrong.

## D. Joint shock and signed components

At USD 10m with A=40%, B=60%, assume A falls 20% while B gains 5%.

- A loss = `10m×0.4×0.20 = USD 800,000`.
- B loss = `10m×0.6×(-0.05) = -USD 300,000` (a gain offset).
- Portfolio loss = USD 500,000 = 5%.
- At 1.5 times these return shocks, loss is USD 750,000 = 7.5% at the same NAV. A severity multiplier is not a probability.

## E. Inspect the actual frozen run

```bash
uv run --locked python run_stress.py
uv run --locked pytest tests/test_stress.py -q
```

Use the output folder printed by the runner. The default folder is `output/stress/20261023T102523Z-0d40a885/200356ee3cbe/`.

1. Confirm `status.json` says `complete`. Check snapshot, as-of, next forecast session, input window, NAV and weights cutoff in `summary.json`.
2. In `contribution_summary.csv`, expect 18 rows; `asset_contributions.csv` has 126. Choose one portfolio/model/measure/confidence, sum its seven component fractions/USD amounts and match the total. Default baseline 99% Normal VaR is approximately USD 108,131.90; Normal ES USD 124,487.34; Historical ES USD 153,489.10. Tolerance USD 0.05 for these rounded references.
3. Read negative/zero components and the historical tail-size warning. Explain why standalone asset ES would answer a different question.
4. In `sizing_checks.csv`, choose a feasible 1 percentage point transfer. Confirm donor decreases, receiver increases, sum remains one, policy is respected, and `after - before = delta`. Compare exact and linear deltas. An infeasible row has a reason and no repriced result; do not select it as a recommendation.
5. In `historical_summary.csv`, confirm nine available rows: three portfolios × three episodes. Per-portfolio expected sessions are 253 (2008), 22 (March 2020), 251 (2022). All 2008 rows must flag `weights_available_at_start=False`.
6. Inspect one NAV/drawdown chart and its CSV peak/trough. For baseline 2022, terminal loss is approximately USD 1,508,312.92 and maximum drawdown 18.947%. Explain the different denominators. All three allocations exceed the proposed 15% review level in 2008 and 2022.
7. In `hypothetical_summary.csv`, base severity loss for baseline is 8.4% / USD 840,000. Its 1.5-times loss is 12.6% / USD 1,260,000 and exceeds the proposed 10% level. Sum the seven asset shock-loss components to verify each selected total.
8. Read `scenario_shocks.csv` and the narrative in `stress_report.md`. Decide whether the joint shock is coherent for your team's interpretation. The displayed development minima are separate historical days, not proof of the hypothetical joint event's likelihood. Approve or revise the assumptions explicitly; rerun and record any change.
9. Explain how one-day ES can be below 2% while a crisis-period drawdown exceeds 15%. Carry the earlier backtesting failures into the investment discussion; neither result proves safety.

## Reviewer record — complete only after doing the work

- Reviewer name:
- Review date:
- Calculator/spreadsheet/paper used:
- Part A calculated VaR/ES and contribution totals:
- Part B calculated tail allocation and explanation of ties:
- Part C terminal loss versus drawdown calculations:
- Part D signed shock contributions:
- Part E exact run folder, selected rows and charts inspected:
- Commands actually run and observed results:
- Discrepancies and corrections (write “None found” only if true):
- In your own words: What is a marginal versus a component contribution?
- In your own words: Why must a fully invested transfer specify its funding asset?
- In your own words: Why is the 2008 replay not the historical performance of our 2018-fitted strategy?
- Scenario decision: accept as a research assumption / revise (give reasons):
- Response to breached review levels and backtesting limitations:
- Reviewer initials/sign-off:

Arithmetic sign-off, scenario approval and final portfolio recommendation are separate decisions. Record concerns even when all calculations match.
