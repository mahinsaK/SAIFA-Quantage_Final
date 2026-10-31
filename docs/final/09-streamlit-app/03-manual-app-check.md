# Manual Streamlit app check

Status: **frontier and heatmap checks reported complete on 27 October 2026; remaining browser checks and reviewer sign-off pending**. Automated evidence is recorded separately in the milestone. Expected values for other checks are not a record that they were performed.

## Start and inspect

```bash
uv run --locked python commands/run_judge_app.py
```

Open the URL printed by Streamlit. If results are absent or incomplete, confirm the app shows a reason and the preparation command. It must not show fabricated sample results. A changed consumed file requires the bundle to be rebuilt.

## A. Portfolio

The optional research extension adds **Research lab** after Purchasing power, linked to “Portfolio research lab”. Check all six panels and their controls using the [Phase 12 worksheet](../12-research-lab/03-manual-research-check.md). This section's human acceptance remains pending; previous app checks do not sign it off.

At the top, check the Portfolio section bar. It should list Summary, Performance, Drawdown, Efficient frontier, Diversification and Purchasing power. Summary must remain visible at the left even when the other links scroll horizontally. Click each label and confirm that it lands on its matching heading: “Selected portfolio at a glance”, “Performance and holdings”, “Drawdown · [selected portfolio]”, “Development-period efficient frontier”, “How do the seven ETFs move together?” and “Purchasing power and spending”. The selected portfolio and calculated results must not change merely from a navigation click, and the bar must remain visible. Scroll manually through these sections and check that the active underline follows the visible section. Check that headings are not hidden behind the bar. The committee view above Summary still needs to remain available. Switch to Risk comparison and confirm the Portfolio section bar disappears. Repeat at a narrow browser width: the remaining labels should scroll horizontally and remain usable. If a browser or layout does not support one of these behaviours, record the exact browser and symptom instead of signing it off.

Select each of the three portfolios. Confirm the target weights, summary metrics and selected drawdown path change correctly; the growth comparison intentionally retains all three portfolios. Check that the evaluation dates, monthly rebalancing, USD 10m and initial/gross trading costs are visible. Baseline ending NAV should be approximately USD 12,448,401.99 on the default snapshot. Confirm blank ratios remain unavailable.

Check the **Development-period efficient frontier** below the drawdown chart. Its horizontal axis is annual volatility and its vertical axis is expected annual return, both in percent. Confirm the caption says the estimates use returns before 2019 and exclude trading costs, while the performance chart above uses realised 2022-onward results after costs. The two marked candidates are close together. Compare the accompanying table with `output/optimisation/<snapshot-id>/candidate_weights.csv`: minimum volatility should be about 6.03% volatility / 5.98% expected return and maximum Sharpe about 6.04% / 6.03%. Do not compare these fitted expected returns directly with the realised evaluation returns.

Check the **How do the seven ETFs move together?** heatmap. It must say daily **return** correlation over 252 aligned sessions, 22 October 2025–22 October 2026 on the default snapshot, and explain that this recent period is not the pre-2019 optimiser input. All seven eligible ETFs should appear on both axes; each diagonal cell should be 1.00 and opposite cells should match. As spot checks, SPY/XLK should be about 0.85 and SPY/AGG about 0.41. The same matrix should remain visible when switching the selected portfolio because it describes the ETF universe, not that portfolio's holdings. Record any unreadable cell labels at a narrow browser width.

Under **Purchasing power and spending**, confirm the observed CPI result changes with the selected portfolio. The approximate annual real-growth figures are 0.68% for 40/60, 2.54% for minimum volatility and 2.71% for maximum Sharpe, each below the proposed 3% objective for the observed period. Check that the period ends 30 September 2026 and that the figures are explicitly **before withdrawals**. The separate 2% inflation spending illustration must remain labelled as an assumption, not observed CPI. Confirm the CPI CSV download and Assumptions page describe the missing October 2025 observation without interpolation. Record any discrepancy; this check does not approve the proposed objective or demonstrate ten-year suitability.

Check that the three-portfolio real-growth chart uses those same values and marks 3% as a **proposed** target. It must not turn the shorter historical observation into a ten-year forecast or show a fabricated daily real-wealth path.

## B. Risk controls

Check that the Risk comparison bar shows Portfolios, Selected estimate and Methods. Each link should land on its matching heading below the sticky bar. Change the selected portfolio, method and confidence; the labels and figures should update while the same three links remain usable.

Select baseline and Historical. At 99%, VaR should be approximately USD 110,505.04 and ES USD 153,489.10. At 90%, Historical VaR should change to USD 51,173.71. Select Parametric Normal and confirm the highlighted metrics change to that method while the comparison table retains all methods. At 90% EVT, compare the headline with the current risk CSV and confirm its boundary explanation: VaR equals the empirical cutoff, while ES is modelled. Use the exact figures in the [boundary review](../06-evt/04-boundary-update.md); neither value should be copied from 95% or 99%. Check all methods share the displayed horizon, as-of window and USD basis.

## C. Backtesting controls

Check that the Backtesting bar shows Overview, the period sections present in the selected dates, Compare models, and Forecasts. An evaluation-only range should omit Validation; a range crossing the validation/evaluation boundary should show both. Each link should land on its heading below the sticky bar without changing the selected dates or recalculated results.

At the top of Backtesting, click **Validation**, **Evaluation** and **All forecasts** in turn. All forecasts covers the complete prepared 2019–2026 backtest period, not the raw market-data history. Confirm the selected dates shown below the buttons and in the sidebar change together, and that the session counts and period headings change. Then set a custom range in the sidebar and use Evaluation to restore the full evaluation range. If the sidebar picker temporarily has only one date, the top buttons should remain visible as a way to recover.

Select baseline, Historical, 99%. For 3 January 2022–22 October 2026, verify 11 exceptions / 1,206 sessions and expected 12.06. Change to 24 October 2025–22 October 2026: verify 1 exception / 250 sessions, expected 2.50 and a green latest Basel window. A range shorter than 250 sessions must have no Basel colour. At 95% there must also be no Basel colour. Select a range spanning 2021 and 2022 and confirm validation/evaluation test results remain separate.

In **Forecasts versus realised losses**, scroll over the chart to zoom dates, drag to pan, and hover a red exception point for its date, forecast VaR, realised loss and amount above VaR. Compare at least one tooltip with the visible **Exact exception dates** table and with `forecasts.csv`. Confirm the table has 11 rows for the baseline Historical 99% evaluation and shrinks when the sidebar date range is shortened. The saved multi-panel PNG in the backtest output remains a static report artifact; the app chart is interactive.

Select 90% EVT: check the dated forecasts and recomputed statistics against the [boundary review](../06-evt/04-boundary-update.md), then shorten the date range and confirm statistics change. Read coverage/clustering failures; available forecasts do not imply a safe model. Genuine missing forecasts must remain missing, and Basel colours remain restricted to 99%. Select an end date before a start date or only one date where the date picker permits it: the app should explain the invalid/incomplete selection. Confirm the sidebar says dates affect backtesting only.

In **Compare model checks**, inspect the portfolio × method matrix for the selected confidence and period. At 99% on the default evaluation dates, the baseline's four Christoffersen cells reject, while minimum-volatility and maximum-Sharpe Normal/Monte Carlo Kupiec cells reject. Shorten the date range and confirm the matrix changes with the selected dates; select 90% EVT and inspect its real availability status. A blue “Not rejected” cell is not model approval. If a period has missing forecasts, its cell must say Unavailable with a reason rather than looking like a pass.

## D. Stress

Check that the Stress analysis bar shows Crisis replay, Compare portfolios, Joint shock and Risk contributions. Each link should land on its matching heading. Change the crisis and severity controls, then confirm the links remain usable and the values still respond to those controls.

For baseline, view 2008 and 2022. Confirm their dates and paths differ and the 2008 warning says the weights were fitted later. Baseline 2022 should show terminal loss about USD 1,508,312.92 and drawdown about 18.95%, with a breach warning. Confirm actual peak/trough values explain drawdown dollars.

In **Compare portfolios**, check the grouped chart contains all three portfolios and the 2008, March 2020 and 2022 replays. Its dashed **15% proposed review level** must match the source table, and 2008 must remain labelled retrospective even when another crisis is selected. Compare one bar with the table; unavailable replays must remain explained instead of being plotted as zero.

For the baseline hypothetical shock, change severity from 1.0 to 1.5. Loss should change from USD 840,000 (8.4%) to USD 1,260,000 (12.6%) and show the proposed 10% trigger breach. Check contribution sums, signed offsets and input units. Confidence changes must affect attribution but must not imply a probability for a crisis or hypothetical event. Monte Carlo/EVT attribution must be explicitly described as unsupported.

In **Risk contributions**, compare the new signed ETF bars with the attribution table for Historical ES and Normal VaR/ES at the selected confidence. Negative bars must remain negative offsets. Switching to Monte Carlo or EVT must show unsupported attribution rather than silently reusing another method's chart.

## E. Readability and evidence

Confirm Assumptions has no section bar.

Read the limitations page. Confirm it includes model failures, retrospective evaluation, proposed risk levels, missing spending information and the distinction between investment approval and software tests. Check labels, table scrolling, chart axes and text at your browser width, including a narrower window. Download one selected risk table and one recalculated backtest table and compare their rows with the current controls. Record the browser used and any corrections needed.

## Reviewer record

- Reviewer name:
- Review date:
- Browser/device/window size:
- Snapshot and bundle reviewed:
- Commands actually run and observed results:
- Part A selections and results checked:
- Part A section navigation and narrow-width behaviour checked: On 27 October 2026, the user reported that Frontier click navigation, persistent visibility during scrolling and automatic active-underline updates worked. Decision and Overview links were unclear and did not land as expected. Summary was pinned outside the horizontally scrolling row, and the user then specified five exact heading destinations for Summary, Performance, Drawdown, Efficient frontier and Diversification. The user subsequently reported that Performance went to “Portfolio performance” instead of “Performance and holdings”. Inspection found that Streamlit automatically assigned `portfolio-performance` to the top heading while the lower heading explicitly used the same anchor. The top heading now uses `portfolio-page` and the Performance link is restored. This correction and narrow-width layout still need browser recheck.
- Part A frontier axes, period and candidate values checked: On 27 October 2026, the user visually checked the graph and its table against the approximate values given in chat, then confirmed that the `candidate_weights.csv` values matched the displayed values. The user also confirmed the displayed annual-volatility and expected-annual-return axes and the caption: "Daily returns before 2019-01-01 were used to fit this curve and the two marked candidates. Both axes are annualised estimates before trading costs. The 2022 onward performance above is a separate, realised comparison after costs." The rest of Part A remains pending.
- Part A heatmap period, axes and spot values checked: On 27 October 2026, the user reported that the requested heatmap checks looked fine in the app. A separate source-data check confirmed a 7×7 symmetric matrix, diagonal 1.00, 22 October 2025–22 October 2026 window, SPY/XLK 0.8508 and SPY/AGG 0.4055. Browser/device details and a narrow-width readability check were not reported.
- Part A observed CPI and separate spending illustration checked:
- Part A purchasing-power navigation and target chart checked:
- Part B confidence/method results checked:
- Part C dates, exceptions and unavailable states checked:
- Part C model-comparison matrix and date-range response checked:
- Part D scenarios, severity and contributions checked:
- Part D cross-crisis and risk-contribution charts checked:
- Part E readability, limitations and downloaded rows checked:
- Discrepancies and corrections:
- Reviewer initials/sign-off:

This worksheet reviews the app's behaviour. It does not approve a portfolio, client policy or team hypothetical scenario.
