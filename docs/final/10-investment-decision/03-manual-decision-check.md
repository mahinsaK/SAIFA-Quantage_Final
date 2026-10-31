# Manual committee and spending review

Status: **team recommendation supplied; Mahinsa Kuruppu (KAD) reported independent accounting, CPI, app and PDF checks on 31 October 2026 with no discrepancy; five-member research scenario accepted**. Client policy/allocation approval remains open.

The named perspectives and team statement in section 3 were supplied by Mahinsa Kuruppu on behalf of the five members on 31 October 2026. They record a team position, not separately signed statements from each member. Mahinsa Kuruppu subsequently reported completing the calculations below; detailed calculator workings were not supplied.

## 1. Small independent accounting examples

Use a calculator or spreadsheet, then compare with `tests/test_spending.py`.

| Example | Inputs | Expected calculation |
|---|---|---|
| A: no returns or costs | USD 1,000; annual payment USD 30; two anniversaries; 0% inflation | Remaining NAV: 1,000 -> 970 -> 940. Total paid 60. Withdrawal is not an investment loss. |
| B: sale fee | USD 1,000 initial capital; 1% initial and sale cost; zero returns | Opening NAV = 1,000/1.01 = 990.0990099. Sell 30/0.99 = 30.3030303; fee 0.3030303; cash paid 30; remaining NAV 959.7959796. Verify NAV + fee + cash = pre-withdrawal NAV. |
| C: indexed payment | Dates 2022-01-03, 2023-01-03, 2024-01-03; initial 1,000; no costs; assumed inflation 10% | First payment 30; next = 30 * 1.10^(365/365.25). Remaining nominal NAV = 1,000 minus both payments. Real ending NAV divides this by 1.10^(730/365.25). Explain why assumed inflation is not actual CPI. |

Record your calculated values: **Mahinsa Kuruppu (KAD) reported independently calculating examples A–C on 31 October 2026 and matching the reference results above. The calculator working sheet and individually calculated values were not supplied.**

Discrepancies and corrections: **None reported by Mahinsa Kuruppu for the completed A–C calculations.**

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
| Observed CPI real-growth objective, before withdrawals | See the [CPI worksheet](04-observed-cpi-review.md): 0.6782% / 2.5418% / 2.7133% per year through 2026-09-30, each below 3% in this shorter historical period. Mahinsa Kuruppu reported independently checking the CPI deflator and one portfolio's annual growth on 31 October. |
| Baseline Historical 99% evaluation exceptions / expected | 11 / 12.06; Kupiec p ~0.7555; independence p ~0.002892 |
| Minimum-volatility 2022 crisis drawdown | 17.4762%, above the proposed 15% review level |

Compare the same figures in the app, PDF report and tear sheet. No-spending values and hypothetical spending values have different cash-flow assumptions; do not compare them as two investment returns.

Figures checked and corrections: **The agent reconciled the team's rounded citations to frozen CSVs. Mahinsa Kuruppu (KAD) reported independently checking the app, all three PDFs and CPI source values on 31 October 2026 with no discrepancy. After the scenario-status and full-name updates, KAD reopened the final 13-page report, one-page tear sheet and one-page memo and confirmed their layout, names and wording; KAD also rechecked the rebuilt Stress page. An itemised comparison sheet was not supplied.**

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
| Mahinsa Kuruppu | Portfolio and preservation: minimum volatility is a conservative research starting point because it minimises estimated development variance, not an approved allocation or protection against future/crisis losses. |
| Lumith Manujaya | Risk and backtesting: baseline Historical 99% has 11 exceptions in 1,206 evaluation sessions; Kupiec p=0.7555 does not reject overall frequency, while independence p=0.002892 warns about clustering. Sparse transition counts limit interpretation. |
| Janith Nishen | Stress: minimum-volatility 2022 replay drawdown is about 17.48%, above the proposed 15% review level. The baseline one-session joint shock loses 8.4% ($840,000), or 12.6% at 1.5x severity; severity is not probability. |
| Rayan Sankalapa | Purchasing power and spending: observed annual real growth before withdrawals is about 0.68% / 2.54% / 2.71% for baseline / minimum volatility / maximum Sharpe, below the proposed 3% objective in the measured period. Actual university spending is unknown. |
| Sandanu Liyanage | Governance: do not implement any of the three tested allocations immediately. Keep minimum volatility for research; clarify spending, liquidity and loss tolerance, address failed tests and stress breaches, and do not raise risk levels simply to make results pass. |

**Team recommendation as supplied:** “We recommend rejecting immediate implementation of the three tested allocations under our current proposed policy. Minimum volatility remains a conditional research candidate. Further consideration requires clarified client needs, additional model validation and an agreed response to the observed risk breaches.” This rejects immediate implementation of these allocations; it does not reject the university's investment mandate or approve a replacement.

Remaining client questions and assigned owners: **Actual spending amounts/dates/currency, near-term liquidity needs, tolerable losses, taxes/fees and approval authority are unknown. The member focus areas above are not a formal assignment of client follow-up owners.**

Hypothetical scenario approval reference: **On 31 October 2026 Mahinsa Kuruppu reported that Mahinsa Kuruppu, Lumith Manujaya, Janith Nishen, Sandanu Liyanage and Rayan Sankalapa accepted the existing joint shock as an illustrative research scenario. See the named record in [the stress worksheet](../08-contributions-stress/03-manual-stress-check.md); individual signatures were not supplied.**

Reviewer name / date: **Mahinsa Kuruppu (KAD), 31 October 2026, reported completing spending examples A–C and cross-checking app, PDFs and CPI with no discrepancy.**

Independent reviewer / date: **Mahinsa Kuruppu (KAD), 31 October 2026, reported independent checks against the generated references; no separate second reviewer was named.**

Sign-off scope and remaining limitations: **KAD's reported sign-off covers examples A–C, final app/PDF figures and CPI source/calculation; the five-member team accepted the illustrative research scenario. The final regenerated PDFs and Stress page were explicitly rechecked. Detailed calculator sheets and browser metadata were not supplied. Client policy approval, actual spending terms and investment authority remain open.**

Only update the status after the named review actually occurs. This worksheet cannot itself grant client investment approval. Confirm GitHub access, final PDF versions, submission route/cutoff and the actual team roster separately.

### Automated audit on 31 October 2026 (not independent human sign-off)

Codex reran the PDF generator using the project's existing Python environment. SHA-256 hashes of all three PDFs were identical before and after regeneration. The frozen bundle and committee evidence loaded successfully; `submission_ready` verified their hashes against the complete PDF manifest and its 13-page report, one-page tear sheet and one-page committee memo. The focused dashboard, decision, spending and stress tests passed **85/85**. This does not record a person reading the final PDFs, independently calculating the spending examples or CPI values, approving the hypothetical scenario, or authorising an investment.
