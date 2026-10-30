# Manual annual-strategy comparison

Status: **pending actual human calculation, output review and interpretation**. Reference answers are not a reviewer record.

## A. Small accounting check

Two assets A/B, USD 1,000 initially, zero returns before the annual update. Hold 100% A initially. On the update date A doubles while B is flat; execute the switch to 100% B **after that close's valuation**. On the following session B doubles while A is flat.

1. With zero costs: opening NAV 1,000; update pre-trade NAV 2,000; post-trade NAV 2,000; next-session NAV 4,000. If you obtain 2,000 at the end, check whether you incorrectly applied the new B target before the update-date A return.
2. With 1% opening/buy/sell costs: `opening = 1000/1.01`; `pre = opening*2`; `post = pre*0.99/1.01`; `fee = 0.01*(pre+post)`; `final = post*2`. Verify `pre = post + fee`. Both the sale and purchase pay costs.

Your calculated values and discrepancies: ______

## B. App and CSV checks

Launch using the README command. Open **Portfolio → Annual strategy**.

Confirm **Read explanation, methodology and limitations** is initially collapsed. Expand it to read the methodology, risk-scope limits and selected annual-minus-frozen interpretation, then collapse it again. The controls, chart and result table should remain available throughout. Keep the short retrospective/pending-risk notice visible.

1. Evaluation dates should be 3 January 2022–22 October 2026; all five candidates start with USD 10m and share the stated gross-trade costs.
2. Compare the displayed evaluation NAVs/costs with the [milestone table](02-adaptive-milestone.md) and `output/adaptive/20261023T102523Z-0d40a885/metrics.csv`.
3. Select Annual minimum volatility, expand the training audit and check 2022 execution on 2022-01-03. Its training boundary is 2017-01-01 inclusive to 2022-01-01 exclusive. Training end must precede execution. Select Annual maximum Sharpe and check the target table and chart change.
4. Switch to Validation. Check the dates change to 2019-01-02–2021-12-31 and that the values change. Both annual variants have lower validation ending wealth than their respective original frozen candidates. Return to Evaluation and check the displayed differences.
5. In `transactions.csv`, filter `evaluation` / `annual_minimum_volatility` / `annual_reoptimisation`. Expect four events after initial funding: the first observed trading sessions in 2023, 2024, 2025 and 2026. Compare each row's `nav_before = nav_after + transaction_cost` and `transaction_cost = gross_traded * 0.001`.
6. In `daily.csv`, inspect 2023-01-03 for that strategy. Pre-trade asset values follow the prior holdings' price change. Post-trade weights should match the new year's audit targets, and the current `*_target` columns should update at that close.
7. Check the sidebar Risk comparison/Backtesting/Stress analysis portfolios remain the three frozen candidates. Their numbers must not be described as adaptive risk results. Check the retrospective/different-window limitations and source-staleness rebuild message where relevant.
8. Check Annual strategy navigation, sticky bar, active underline and narrow-screen layout in your browser. Automated AppTest does not verify actual scrolling.

Outputs checked and corrections: ______

## C. Interpretation

- Why does annual re-optimisation differ from monthly rebalancing?
- Why do the old holdings earn the annual execution date's return?
- Why can a higher ending NAV coexist with higher risk and costs?
- Why must the weaker validation results be retained alongside the stronger maximum-Sharpe evaluation result?
- Why does using a trailing-five-year window as well as annual updates prevent isolating the effect of update frequency alone?
- What additional adaptive risk/spending tests are needed before a committee could consider this allocation?

Your explanation and decision about further research: ______

Reviewer name/date: ______

Independent reviewer/date: ______

Sign-off scope and remaining limitations: ______

Do not mark this complete until the actual review occurs. This worksheet cannot approve client policy, a scenario or an investment allocation.
