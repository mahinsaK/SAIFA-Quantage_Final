# Manual contributions and stress check

Status: **Parts A–D signed off; Mahinsa Kuruppu (KAD) reported completing the remaining Part E output-file checks on 31 October 2026; the five-member team accepted the illustrative research scenario**. Client investment approval remains open.

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
|------------:|-------:|-------:|---:  |
| 1           | 0.04   | 0.00   | 0.02 |
| 2           | 0.02   | 0.02   | 0.02 |
| 3           | 0.03   | 0.01   | 0.02 |
| 4           | 0.00   | 0.00   | 0.00 |

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
uv run --locked python commands/run_stress.py
uv run --locked pytest tests/test_stress.py -q
```

Use the output folder printed by the runner. After the 31 October scenario-status update, the default folder is `output/stress/20261023T102523Z-0d40a885/7850adac5c53/`. The earlier `200356ee3cbe` run remains historical evidence with the same shock percentages but an older pending-review label.

1. Confirm `status.json` says `complete`. Check snapshot, as-of, next forecast session, input window, NAV and weights cutoff in `summary.json`.
2. In `contribution_summary.csv`, expect 18 rows; `asset_contributions.csv` has 126. Choose one portfolio/model/measure/confidence, sum its seven component fractions/USD amounts and match the total. Default baseline 99% Normal VaR is approximately USD 108,131.90; Normal ES USD 124,487.34; Historical ES USD 153,489.10. Tolerance USD 0.05 for these rounded references.
3. In the app, select Stress analysis → Risk contributions, baseline, 99% and Historical. Read the small-tail warning above the totals table and confirm the same limitation in `contribution_summary.csv`; it refers to ten effective observations. Read negative/zero components and explain why standalone asset ES would answer a different question.
4. In `sizing_checks.csv`, choose a feasible 1 percentage point transfer. Confirm donor decreases, receiver increases, sum remains one, policy is respected, and `after - before = delta`. Compare exact and linear deltas. An infeasible row has a reason and no repriced result; do not select it as a recommendation.
5. In `historical_summary.csv`, confirm nine available rows: three portfolios × three episodes. Per-portfolio expected sessions are 253 (2008), 22 (March 2020), 251 (2022). All 2008 rows currently flag `weights_available_at_start=False` because the field uses the shared 2018 fitting cutoff. The baseline 40/60 weights are preset, not estimated from 2018 data; the flag is a limitation of this metadata field for that row.
6. Inspect one NAV/drawdown chart and its CSV peak/trough. For baseline 2022, terminal loss is approximately USD 1,508,312.92 and maximum drawdown 18.947%. Explain the different denominators. All three allocations exceed the proposed 15% review level in 2008 and 2022.
7. In `hypothetical_summary.csv`, base severity loss for baseline is 8.4% / USD 840,000. Its 1.5-times loss is 12.6% / USD 1,260,000 and exceeds the proposed 10% level. Sum the seven asset shock-loss components to verify each selected total.
8. Read `scenario_shocks.csv` and the narrative in `stress_report.md`. Decide whether the joint shock is coherent for your team's interpretation. The displayed development minima are separate historical days, not proof of the hypothetical joint event's likelihood. Approve or revise the assumptions explicitly; rerun and record any change.
9. Explain how one-day ES can be below 2% while a crisis-period drawdown exceeds 15%. Carry the earlier backtesting failures into the investment discussion; neither result proves safety.

## Reviewer record — complete only after doing the work

- Reviewer name: Mahinsa Kuruppu
- Review date: 25 Oct 2026
- Calculator/spreadsheet/paper used: Calculator

- Part A calculated VaR/ES and contribution totals: Verified as shown above.
- Part B calculated tail allocation and explanation of ties: Verified as shown above.
- Part C terminal loss versus drawdown calculations: Verified as shown above.
- Part D signed shock contributions: Verified as shown above.

- Part E exact run folder, selected rows and charts inspected: Baseline `2022_rate_shock` replay checked in the Stress analysis page against `historical_summary.csv` on 29 Oct 2026. The reviewer confirmed 251 sessions, USD 1,508,312.92 terminal loss, 18.947% maximum drawdown, an October 2022 trough, and a breach of the proposed 15% drawdown review level.
- Part E baseline `2008_GFC` app check: On 29 Oct 2026, the reviewer reported that all requested values and the retrospective warning matched the frozen CSV references: 253 sessions, USD 997,795.78 terminal loss, 21.74% maximum drawdown, USD 2,191,458.25 peak-to-trough loss, a proposed 15% review-level breach, and the displayed 19 May peak / 10 October trough. This is a reviewer-reported app check, not approval of the replay as a historical investment track record.
- Part E baseline `March_2020` app check: On 29 Oct 2026, the reviewer reported that the requested 22/22 sessions, USD 531,091.29 terminal loss, 14.67% maximum drawdown, USD 1,504,677.35 peak-to-trough loss and absence of a proposed 15% breach warning all matched the frozen CSV references. The replay covers March only, not the whole of 2020.
- Part E cross-portfolio crisis chart: On 29 Oct 2026, the reviewer reported that all nine drawdown bars, the proposed 15% line and the table changing with the selected crisis matched the frozen summary. Drawdowns were 21.74% / 16.32% / 16.35% in 2008, 14.67% / 11.75% / 11.72% in March 2020, and 18.95% / 17.48% / 17.68% in 2022 for baseline / minimum volatility / maximum Sharpe. All three exceed the proposed level in 2008 and 2022; none does in March 2020. This records an app visual check, not team approval of the review level or an investment.
- Part E baseline hypothetical joint-shock app check: On 29 Oct 2026, after the one-session scenario and severity multiplier were explained, the reviewer reported that the displayed values matched the frozen output. At severity 1.0, SPY USD 480,000 plus AGG USD 360,000 gave USD 840,000 / 8.4%, without a proposed 10% breach. At severity 1.5, SPY USD 720,000 plus AGG USD 540,000 gave USD 1,260,000 / 12.6%, with a breach warning. The five zero-weight ETF components were zero. This confirms displayed arithmetic and controls, not the team-designed scenario assumptions or their probability.
- Part E baseline 99% Parametric Normal attribution app check: On 29 Oct 2026, the reviewer reported that SPY and AGG VaR components were USD 77,374.28 and 30,757.63 against the USD 108,131.90 total; ES components were USD 89,106.19 and 35,381.15 against the USD 124,487.34 total. The unrounded source components reconcile exactly; individually rounded VaR cents sum to USD 108,131.91, one cent above the rounded total. The other five zero-weight ETFs contributed zero. This is a selected one-session model attribution check, not validation of its forecasts.
- Part E feasible funded-transfer app check: On 29 Oct 2026, the reviewer reported that transferring one percentage point from SPY to EFA at 95% Parametric Normal VaR preserved full investment (39% SPY, 1% EFA, 60% AGG) and matched USD 75,239.47 before, USD 75,047.08 after, exact delta −USD 192.39 and linear approximation −USD 199.47. This is a risk sensitivity, not a trade recommendation.
- Remaining Part E checks and team scenario approval: Mahinsa Kuruppu (KAD) reported checking the status/summary files, 18/126 contribution rows, ten-observation warning, sizing CSV, nine crisis rows and component sums on 31 October 2026, along with the app A–E checks, with no discrepancy. The five-member team acceptance was reported separately on the same date. Detailed row-by-row workings were not supplied.
- Commands actually run and observed results: Mahinsa Kuruppu reported completing the checks on 31 October 2026; the exact human command log was not supplied. Codex's separate automated audit below passed.
- Discrepancies and corrections (write “None found” only if true): None found in the completed checks; remaining Part E outputs and assumptions are not yet signed off.

- In your own words: What is a marginal versus a component contribution?
  A marginal contribution measures how risk changes for a tiny increase in an asset's weight. A component contribution is the asset's weight multiplied by its marginal contribution, representing that asset's share of total portfolio risk.

- In your own words: Why must a fully invested transfer specify its funding asset?
  Because increasing one asset's weight requires decreasing another asset's weight so that total weights still sum to 100%. The risk impact depends on both sides of the trade.

- In your own words: Why is the 2008 replay not the historical performance of our 2018-fitted strategy?
  A replay applies today's model or portfolio structure to historical market data. It is a stress experiment, not evidence that the strategy actually existed and traded during that period.

- Scenario decision: accept as a research assumption / revise (give reasons):

  Accepted by the team as an illustrative, severe one-session research scenario. We reviewed the seven ETF shocks and the inflation/liquidity-squeeze narrative. The shocks are simultaneous assumptions, not a historically observed joint day, a calibrated probability, or a forecast. We retain the 0.5×, 1× and 1.5× results to show sensitivity; the 1.5× case breaches our proposed 10% review level for all three portfolios. This acceptance does not approve an investment allocation or client risk limit.

  Mahinsa Kuruppu reported acceptance by Mahinsa Kuruppu, Lumith Manujaya, Janith Nishen, Sandanu Liyanage and Rayan Sankalapa on 31 October 2026. This is a team-reported decision; individual signatures were not supplied.

- Response to breached review levels and backtesting limitations:
  Drawdown breaches and backtesting failures should be treated as risk warnings requiring investigation. Passing one risk measure does not prove safety.
- Reviewer initials/sign-off (Parts A–D): KAD

Arithmetic sign-off, scenario approval and final portfolio recommendation are separate decisions. Record concerns even when all calculations match.

### Automated audit on 31 October 2026 (not scenario approval)

Codex ran the focused dashboard, decision, spending and stress tests: **85 passed**. The frozen app bundle and committee evidence loaded successfully, and the generated PDF manifest passed `submission_ready`. The stress run's scenario inputs remain SPY −12%, EFA −15%, EEM −18%, AGG −6%, GLD −4%, XLE −20% and XLK −18%; the base baseline shock remains 8.4% / USD 840,000 and its 1.5× sensitivity 12.6% / USD 1,260,000. The team's subsequent acceptance is recorded above; this automated audit did not constitute that decision.
