# Manual optimisation and performance check

Status: **human review pending**.

This worksheet verifies a few transparent identities. It does not ask a person to reproduce the numerical optimiser by hand.

## Part A: policy constraints

Open `output/optimisation/<snapshot-id>/candidate_weights.csv` and verify each candidate:

1. All seven weights are at least 0% and no weight exceeds 60%.
2. The seven weights sum to 100% within 0.0001%.
3. AGG is at least 40%.
4. SPY + EFA + EEM + XLE + XLK is at most 50%.
5. XLE and XLK are each at most 10%, and together at most 15%.
6. GLD is at most 20%.

## Part B: two-asset volatility example

Use weights 40% and 60%, annual volatilities 20% and 10%, and correlation 0.25.

Calculate:

`variance = 0.4^2 * 0.2^2 + 0.6^2 * 0.1^2 + 2 * 0.4 * 0.6 * 0.2 * 0.1 * 0.25`

Expected variance: `0.0124`.

Expected volatility: `sqrt(0.0124) = 0.1113552873`, or approximately **11.1355%**.

This confirms why covariance matters: portfolio risk is not the weighted average of individual volatilities.

## Part C: CAPM example

If a portfolio has an annual return of 8%, the risk-free rate is 2%, beta is 0.5, and the market return is 10%:

`Jensen alpha = (8% - 2%) - 0.5 * (10% - 2%) = 2%`.

`Treynor ratio = (8% - 2%) / 0.5 = 12%`.

Confirm that positive alpha means the portfolio return exceeded the CAPM-implied return for this sample. It does not prove manager skill or future outperformance.

## Part D: automated checks

Run:

```bash
uv run --locked pytest tests/test_optimisation.py -q
uv run --locked pytest -q
uv run --locked ruff check .
```

## Human review record

- Reviewer name: Mahinsa Kuruppu
- Review date: 23 Oct 2026
- Calculator/spreadsheet/paper used:
- Part A matched within tolerance: Yes 
- Part B matched within tolerance: Yes 
- Part C matched within tolerance: Yes 
- Automated commands and results:

.......                                      [100%]
7 passed in 0.57s
.......................................      [100%]
39 passed in 1.12s
All checks passed!

- Discrepancies and corrections:
 None. The manually calculated constraint, portfolio volatility, Jensen alpha and Treynor ratio values matched the expected values within the stated rounding tolerance.
- Reviewer explanation in own words: Why can the optimiser's historical maximum-Sharpe portfolio fail to outperform later?
The maximum-Sharpe portfolio is selected using historical returns, volatility and correlations. These values can change in the future because market conditions, interest rates and relationships between assets can change. Expected returns are also difficult to estimate accurately. Therefore, a portfolio that had the highest estimated Sharpe ratio in the development period may have lower returns or higher risk in a later period. Transaction costs and estimation errors can also reduce its actual performance.
- Reviewer initials/sign-off: KAD

This review validates selected calculations and constraint interpretation only. It does not approve the candidate as the endowment recommendation.
