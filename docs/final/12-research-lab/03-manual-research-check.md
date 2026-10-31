# Manual research-lab review

Status: **pending actual human calculation, output review and interpretation**. Reference numbers below are not a reviewer record. Do not change earlier worksheets or approvals based on passing software tests.

## Start

Run the usual app command from README, then select **Research lab** in the sidebar. The research-question selector opens six panels. Read the scope expander before interpreting results; the main sidebar's portfolio/risk selectors and the Portfolio page's committee view still refer to the original frozen candidates. The annual-weight experiment is in its separate PR.

## A. Alternative allocations

1. Select Evaluation and Minimum historical ES. Compare the 2022-01-03–2026-10-22 table with `output/research/20261023T102523Z-0d40a885/candidate_metrics.csv`. Expected NAV **13,555,828.31**, volatility **8.1825%**, drawdown loss **17.0430%**. Switch to risk parity: NAV **13,345,894.86**, volatility **7.7881%**, drawdown loss **15.5110%**.
2. Check seven target weights total 100% and respect the policy. Check variance-risk shares sum to 100%, although they need not equal capital weights or one another.
3. Read the risk-parity equality flag and maximum gap. It must not claim perfect equal risk when the policy-constrained result only comes close.
4. Switch to Validation. Check NAVs **14,046,484.78 / 13,529,836.01**, not unchanged evaluation values.
5. Hand example: if all assets lose 1% every session except AGG losing 0.5%, and AGG's cap is 60%, the attainable minimum loss/ES is `0.6*0.005 + 0.4*0.01 = 0.007` (0.7%). Why does this not guarantee future tail losses?

Your checks, calculations and corrections: ______

## B. Robustness

1. Select each original objective. Read training-only variant labels, successful/failed counts and block-weight dispersion.
2. Check `robustness_weights.csv` has no evaluation-based winner selection. Compare a variant's seven weights with original `allocation_weights.csv` and calculate half the sum of absolute weight changes.
3. Hand example: 40% SPY/60% AGG changes to 35% SPY/60% AGG/5% GLD. One-way target distance is `(5%+0%+5%)/2 = 5%`, not 10%.
4. Explain why thirty resample percentiles are descriptive sensitivity rather than a guarantee that future optimal weights fall inside them.

Your explanation and corrections: ______

## C. Volatility/dependence

1. Select baseline, GARCH Normal and 99%. In `volatility_forecasts.csv`, apply all four filters: `strategy = baseline_40_60`, `method = garch_normal`, `confidence = 0.99`, `forecast_date = 2026-10-22`. This identifies one row. Compare its target/as-of date and USD VaR/ES with the latest app result over the full evaluation range. A forecast target must follow its as-of date; `parameter_fit_end` must not follow the as-of date.
2. Change dates to a shorter period and verify observation/exception counts change. Read selected coverage/independence warnings; missing or insufficient tests must be unavailable. Compare GARCH FHS, EWMA and Historical reference using the same range/confidence.
3. Open fit evidence. There are 24 converged annual fits on this snapshot; a converged fit is not evidence of calibrated tails. Check at least one rejected coverage/independence result rather than looking only at non-rejections.
4. Hand recursion: with initial variance 2, omega 0.1, alpha 0.2, beta 0.5 and shocks 1 then 2, subsequent variances are **1.3** and **1.55**. Tomorrow's shock cannot affect today's forecast.
5. Inspect SPY/AGG, SPY/GLD and SPY/XLK correlation paths. Explain why a time-varying EWMA line is not a fitted DCC/copula model, and why prior-volatility labels are not a Markov-switching model.

Selected rows, dates, interpretations and corrections: ______

## D. Long-horizon spending

1. Select baseline, 3% withdrawal and 0% extra inflation uplift. Check 1,000 paths and 120 months. Source is **54 complete monthly rows, February 2022–September 2026**; October/November 2025 inflation ratios must be excluded without filling.
2. Check median ending real wealth **11,093,950.38**, 5th percentile **6,710,948.00**, no-shortfall frequency **100%**, and preserved-real-capital fraction **63.5%** in the expanded evidence. Explain why paying every withdrawal is different from preserving capital.
3. Change withdrawal to 4% and then add the 2% compounded annual inflation uplift. Confirm both values and the quantile curves change. The uplift multiplies the inflation-growth factor; it is not an observed forecast rate.
4. Hand example: capital 1,000, no returns/fees/inflation and annual payments 30 leads to **970 then 940**. With 10% annual inflation, first payment remains 30 and the next is 33. With a 1% sale cost, sell `30/0.99` to deliver cash 30.
5. Explain why all 1,000 paths succeeding and a narrow Monte Carlo interval cannot establish actual ten-year university sustainability. Mention the short recent source, missing earlier crises, structural change and unknown actual spending.

Your calculations and interpretation: ______

## E. Income and costs

1. Baseline's constant-notional ex-date proxy is **1,218,710.47**. Compare the ledger with raw SPY/AGG distribution rows; use the **previous** Close. Do not add it to adjusted-price total returns.
2. Select a portfolio holding XLK/XLE. The complete total should be unavailable with the 2025 split-unit review reason. Partial ledger rows are not the missing complete fund-income total. Actual payment dates and taxes remain unknown even for baseline.
3. Cost panel: select the same portfolio/period, vary gross-trade cost 0/10/25 bps and extra admin fee 0/25/50 bps. Compare `cost_metrics.csv`. Confirm ETF expenses are not charged again.
4. Independent cost example: rotating all 1,000 from A into B with 1% cost on sells and buys leaves `1000*0.99/1.01`. Verify gross traded is the old NAV plus the new NAV and `old NAV = new NAV + fee`.
5. Inspect one liquidity row: divide absolute trade USD by prior-20-session mean `Close*Volume`. Today's volume must be excluded. Explain why low participation is not proof of low spread/impact or guaranteed execution.

Your calculations, missing inputs and corrections: ______

## F. Human acceptance and decision

Reviewer name/date: ______

Independent reviewer/date: ______

Actual panels/CSV rows checked: ______

Desktop/narrow-screen navigation and collapsed explanations checked: ______

What evidence supports further research, and what evidence challenges it? ______

What needs fresh validation or additional data before committee use? ______

Decision about including this experimental branch in the submission: ______

Remaining limitations and assigned owners: ______

Only record sign-off after the actual work occurs. This worksheet cannot grant policy, scenario or investment approval.
