# Manual Streamlit app check

Status: **pending actual browser inspection and reviewer sign-off**. Automated evidence is recorded separately in the milestone. Expected values are checks to perform, not a record that you already performed them.

## Start and inspect

```bash
uv run --locked python commands/run_judge_app.py
```

Open the URL printed by Streamlit. If results are absent or incomplete, confirm the app shows a reason and the preparation command. It must not show fabricated sample results. A changed consumed file requires the bundle to be rebuilt.

## A. Portfolio

Select each of the three portfolios. Confirm the target weights, summary metrics and selected drawdown path change correctly; the growth comparison intentionally retains all three portfolios. Check that the evaluation dates, monthly rebalancing, USD 10m and initial/gross trading costs are visible. Baseline ending NAV should be approximately USD 12,448,401.99 on the default snapshot. Confirm blank ratios remain unavailable.

## B. Risk controls

Select baseline and Historical. At 99%, VaR should be approximately USD 110,505.04 and ES USD 153,489.10. At 90%, Historical VaR should change to USD 51,173.71. Select Parametric Normal and confirm the highlighted metrics change to that method while the comparison table retains all methods. At 90% EVT, the headline must show Unavailable and explain the threshold boundary; it must not show a number copied from 95% or 99%. Check all methods share the displayed horizon, as-of window and USD basis.

## C. Backtesting controls

Select baseline, Historical, 99%. For 3 January 2022–22 October 2026, verify 11 exceptions / 1,206 sessions and expected 12.06. Change to 24 October 2025–22 October 2026: verify 1 exception / 250 sessions, expected 2.50 and a green latest Basel window. A range shorter than 250 sessions must have no Basel colour. At 95% there must also be no Basel colour. Select a range spanning 2021 and 2022 and confirm validation/evaluation test results remain separate.

Select 90% EVT: the forecast rows remain unavailable, the tests must not pass, and an unavailable exception count must not be interpreted as zero losses. Select an end date before a start date or only one date where the date picker permits it: the app should explain the invalid/incomplete selection. Confirm the sidebar says dates affect backtesting only.

## D. Stress

For baseline, view 2008 and 2022. Confirm their dates and paths differ and the 2008 warning says the weights were fitted later. Baseline 2022 should show terminal loss about USD 1,508,312.92 and drawdown about 18.95%, with a breach warning. Confirm actual peak/trough values explain drawdown dollars.

For the baseline hypothetical shock, change severity from 1.0 to 1.5. Loss should change from USD 840,000 (8.4%) to USD 1,260,000 (12.6%) and show the proposed 10% trigger breach. Check contribution sums, signed offsets and input units. Confidence changes must affect attribution but must not imply a probability for a crisis or hypothetical event. Monte Carlo/EVT attribution must be explicitly described as unsupported.

## E. Readability and evidence

Read the limitations page. Confirm it includes model failures, retrospective evaluation, proposed risk levels, missing spending information and the distinction between investment approval and software tests. Check labels, table scrolling, chart axes and text at your browser width, including a narrower window. Download one selected risk table and one recalculated backtest table and compare their rows with the current controls. Record the browser used and any corrections needed.

## Reviewer record

- Reviewer name:
- Review date:
- Browser/device/window size:
- Snapshot and bundle reviewed:
- Commands actually run and observed results:
- Part A selections and results checked:
- Part B confidence/method results checked:
- Part C dates, exceptions and unavailable states checked:
- Part D scenarios, severity and contributions checked:
- Part E readability, limitations and downloaded rows checked:
- Discrepancies and corrections:
- Reviewer initials/sign-off:

This worksheet reviews the app's behaviour. It does not approve a portfolio, client policy or team hypothetical scenario.
