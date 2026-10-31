# Manual committee and spending review

Status: **team recommendation supplied on 31 October 2026; independent accounting, CPI, scenario and document sign-offs remain pending**.

The named perspectives and team statement in section 3 were supplied by Mahinsa on behalf of the five members on 31 October 2026. They record a team position, not separately signed statements from each member or completion of the calculations below. Expected values remain reference answers until a reviewer records actual checks.

## 1. Small independent accounting examples

Use a calculator or spreadsheet, then compare with `tests/test_spending.py`.

| Example | Inputs | Expected calculation |
|---|---|---|
| A: no returns or costs | USD 1,000; annual payment USD 30; two anniversaries; 0% inflation | Remaining NAV: 1,000 -> 970 -> 940. Total paid 60. Withdrawal is not an investment loss. |
| B: sale fee | USD 1,000 initial capital; 1% initial and sale cost; zero returns | Opening NAV = 1,000/1.01 = 990.0990099. Sell 30/0.99 = 30.3030303; fee 0.3030303; cash paid 30; remaining NAV 959.7959796. Verify NAV + fee + cash = pre-withdrawal NAV. |
| C: indexed payment | Dates 2022-01-03, 2023-01-03, 2024-01-03; initial 1,000; no costs; assumed inflation 10% | First payment 30; next = 30 * 1.10^(365/365.25). Remaining nominal NAV = 1,000 minus both payments. Real ending NAV divides this by 1.10^(730/365.25). Explain why assumed inflation is not actual CPI. |

Record your calculated values: **Pending independent human calculation; none was supplied with the team position.**

Discrepancies and corrections: **Pending that calculation.**

## 2. Check frozen output figures

Run `uv run --locked python commands/run_submission.py` and require complete manifests. Open the CSVs in `output/decision/20261023T102523Z-0d40a885/`.

| Check | Expected |
|---|---|
| No-spending final NAV: baseline / minimum volatility / maximum Sharpe | USD 12,448,401.99 / 13,427,240.20 / 13,512,711.30 |
| 2% assumed inflation, minimum volatility: ending nominal wealth | USD 11,847,609.14 |
| Same scenario: ending scenario-real wealth | USD 10,773,445.10 |
| Same scenario: real remaining-capital growth | 1.564354% per year; below the stricter 3% after-spending test |
| Same scenario: total cash paid / withdrawal-sale fees | USD 1,236,525.55 / 1,237.76 |
| Payment dates | 2023-01-03; 2024-01-03; 2025-01-03; 2026-01-05 |
| Observed CPI real-growth objective, before withdrawals | See the [new CPI worksheet](04-observed-cpi-review.md): 0.6782% / 2.5418% / 2.7133% per year through 2026-09-30, each below 3% in this shorter historical period. Independent human calculation remains pending. |
| Baseline Historical 99% evaluation exceptions / expected | 11 / 12.06; Kupiec p ~0.7555; independence p ~0.002892 |
| Minimum-volatility 2022 crisis drawdown | 17.4762%, above the proposed 15% review level |

Compare the same figures in the app, PDF report and tear sheet. No-spending values and hypothetical spending values have different cash-flow assumptions; do not compare them as two investment returns.

Figures checked and corrections: **The team-provided interpretation cites the rounded backtest, 2022 drawdown, joint-shock and CPI figures. The agent reconciled those citations to the frozen CSVs; an independent human cross-check of all report/app/PDF values is still pending.**

## 3. Team interpretation and decision

Answer independently:

- Why can a smaller one-day ES coexist with a crisis drawdown above the review level?
- Why is minimum volatility only a conditional discussion candidate rather than an approved allocation?
- Why do withdrawals require selling more than the cash payment when fees apply?
- What can the observed CPI comparison show, and why do missing actual spending details and a shorter historical period still prevent a ten-year suitability claim?
- Do the hypothetical inflation assumptions and payment timing suit the question we want to explore?
- How should the committee respond to the drawdown and severe-shock breaches? Do not change limits solely to make these results pass.
- Does the team accept, revise or reject the AI-assisted draft recommendation, and why?

### Recorded member perspectives

| Member | Focus and position supplied by the team |
|---|---|
| Mahinsa | Portfolio and preservation: minimum volatility is a conservative research starting point because it minimises estimated development variance, not an approved allocation or protection against future/crisis losses. |
| Lumith | Risk and backtesting: baseline Historical 99% has 11 exceptions in 1,206 evaluation sessions; Kupiec p=0.7555 does not reject overall frequency, while independence p=0.002892 warns about clustering. Sparse transition counts limit interpretation. |
| Janith | Stress: minimum-volatility 2022 replay drawdown is about 17.48%, above the proposed 15% review level. The baseline one-session joint shock loses 8.4% ($840,000), or 12.6% at 1.5x severity; severity is not probability. |
| Rayan | Purchasing power and spending: observed annual real growth before withdrawals is about 0.68% / 2.54% / 2.71% for baseline / minimum volatility / maximum Sharpe, below the proposed 3% objective in the measured period. Actual university spending is unknown. |
| Sandanu | Governance: do not implement any of the three tested allocations immediately. Keep minimum volatility for research; clarify spending, liquidity and loss tolerance, address failed tests and stress breaches, and do not raise risk levels simply to make results pass. |

**Team recommendation as supplied:** “We recommend rejecting immediate implementation of the three tested allocations under our current proposed policy. Minimum volatility remains a conditional research candidate. Further consideration requires clarified client needs, additional model validation and an agreed response to the observed risk breaches.” This rejects immediate implementation of these allocations; it does not reject the university's investment mandate or approve a replacement.

Remaining client questions and assigned owners: **Actual spending amounts/dates/currency, near-term liquidity needs, tolerable losses, taxes/fees and approval authority are unknown. The member focus areas above are not a formal assignment of client follow-up owners.**

Hypothetical scenario approval reference (if actually completed): **Not supplied; team scenario review remains open.**

Reviewer name / date: **Mahinsa supplied the team perspectives on 31 October 2026; no individual calculation or document-review signature supplied here.**

Independent reviewer / date: **Pending.**

Sign-off scope and remaining limitations: **Team recommendation wording recorded only. Manual examples, full output/PDF acceptance, CPI source check, scenario approval, client policy approval and investment authority remain open.**

Only update the status after the named review actually occurs. This worksheet cannot itself grant client investment approval. Confirm GitHub access, final PDF versions, submission route/cutoff and the actual team roster separately.
