# Manual committee and spending review

Status: **pending actual human calculation, interpretation and team decision**.

Expected values below are reference answers, not a completed reviewer record. Record differences and explain your decision in your own words.

## 1. Small independent accounting examples

Use a calculator or spreadsheet, then compare with `tests/test_spending.py`.

| Example | Inputs | Expected calculation |
|---|---|---|
| A: no returns or costs | USD 1,000; annual payment USD 30; two anniversaries; 0% inflation | Remaining NAV: 1,000 -> 970 -> 940. Total paid 60. Withdrawal is not an investment loss. |
| B: sale fee | USD 1,000 initial capital; 1% initial and sale cost; zero returns | Opening NAV = 1,000/1.01 = 990.0990099. Sell 30/0.99 = 30.3030303; fee 0.3030303; cash paid 30; remaining NAV 959.7959796. Verify NAV + fee + cash = pre-withdrawal NAV. |
| C: indexed payment | Dates 2022-01-03, 2023-01-03, 2024-01-03; initial 1,000; no costs; assumed inflation 10% | First payment 30; next = 30 * 1.10^(365/365.25). Remaining nominal NAV = 1,000 minus both payments. Real ending NAV divides this by 1.10^(730/365.25). Explain why assumed inflation is not actual CPI. |

Record your calculated values: ______

Discrepancies and corrections: ______

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

Figures checked and corrections: ______

## 3. Team interpretation and decision

Answer independently:

- Why can a smaller one-day ES coexist with a crisis drawdown above the review level?
- Why is minimum volatility only a conditional discussion candidate rather than an approved allocation?
- Why do withdrawals require selling more than the cash payment when fees apply?
- What can the observed CPI comparison show, and why do missing actual spending details and a shorter historical period still prevent a ten-year suitability claim?
- Do the hypothetical inflation assumptions and payment timing suit the question we want to explore?
- How should the committee respond to the drawdown and severe-shock breaches? Do not change limits solely to make these results pass.
- Does the team accept, revise or reject the AI-assisted draft recommendation, and why?

Team's own recommendation and supporting evidence: ______

Remaining client questions and assigned owners: ______

Hypothetical scenario approval reference (if actually completed): ______

Reviewer name / date: ______

Independent reviewer / date: ______

Sign-off scope and remaining limitations: ______

Only update the status after the named review actually occurs. This worksheet cannot itself grant client investment approval. Confirm GitHub access, final PDF versions, submission route/cutoff and the actual team roster separately.
