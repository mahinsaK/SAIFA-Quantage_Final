# Manual portfolio accounting check

Status: **human accounting validation completed on 23 October 2026**.

This is the small independent check the team must perform. Do not use the portfolio code to calculate the answers. A calculator, paper, or a separate spreadsheet is suitable. The purpose is to confirm that a team member understands the accounting and can explain it to judges.

## Example inputs

- Starting portfolio value before the market move: USD 100.00.
- SPY value: USD 40.00.
- AGG value: USD 60.00.
- SPY daily return: +10%.
- AGG daily return: 0%.
- Target weights after rebalancing: 40% SPY / 60% AGG.
- Transaction cost: 10 bps = 0.10% = 0.001 of absolute buys plus absolute sells.

## Part A: market movement before rebalancing

Calculate these independently:

1. SPY value after its return.
2. AGG value after its return.
3. Pre-trade portfolio NAV.
4. SPY and AGG weights before rebalancing.
5. Portfolio daily return before rebalancing cost.

Expected values for comparison after you calculate:

| Quantity | Expected value |
|---|---:|
| SPY value | 44.0000000000 |
| AGG value | 60.0000000000 |
| Pre-trade NAV | 104.0000000000 |
| SPY weight | 42.3076923077% |
| AGG weight | 57.6923076923% |
| Pre-cost portfolio return | 4.0000000000% |

## Part B: no-cost rebalance

Calculate target dollar values and signed trades. A negative trade means sell; a positive trade means buy.

| Quantity | Expected value |
|---|---:|
| Target SPY value | 41.6000000000 |
| Target AGG value | 62.4000000000 |
| SPY trade | -2.4000000000 |
| AGG trade | +2.4000000000 |
| Gross traded amount | 4.8000000000 |
| Transaction cost | 0.0000000000 |
| Post-trade NAV | 104.0000000000 |

Confirm that buys equal sells and the post-trade weights are exactly 40% and 60%.

## Part C: exact 10 bps rebalance

An approximate cost of `4.8 * 0.001 = 0.0048` is close but not exact, because paying cost slightly reduces target NAV and therefore slightly changes both target values and trades.

Solve or verify:

`x + 0.001 * (abs(0.4*x - 44) + abs(0.6*x - 60)) = 104`

For this example SPY is sold and AGG is bought, so the equation can be written:

`x + 0.001 * ((44 - 0.4*x) + (0.6*x - 60)) = 104`

Expected values:

| Quantity | Expected value |
|---|---:|
| Post-cost NAV x | 103.9952009598 |
| Target SPY value | 41.5980803839 |
| Target AGG value | 62.3971205759 |
| SPY trade | -2.4019196161 |
| AGG trade | +2.3971205759 |
| Gross traded amount | 4.7990401920 |
| Transaction cost | 0.0047990402 |

Verify all four identities with rounding tolerance of USD 0.000001:

1. SPY value + AGG value = post-cost NAV.
2. Post-cost NAV + transaction cost = USD 104.
3. SPY trade + AGG trade = negative transaction cost.
4. Cost = 0.001 × gross traded amount.

## Compare with the automated test

After completing the calculations, run only the matching automated examples:

```bash
uv run --locked pytest tests/test_portfolio.py -q
```

The hand example is implemented in `test_hand_example_drift_and_exact_costed_rebalance` and `test_two_day_portfolio_matches_hand_calculation_without_cost`. Read those tests and confirm the expected values match your independent calculation. Do not mark human validation complete merely because pytest passes.

## Human review record

Recorded from the team member's confirmation in the project conversation:

- Reviewer name: Mahinsa Kuruppu
- Review date: 2026-10-23
- Calculator/spreadsheet/paper used: Calculator & paper
- Part A matched within tolerance: Yes - team member reported the calculated values were the same
- Part B matched within tolerance: Yes - team member reported the calculated values were the same
- Part C matched within tolerance: Yes - team member reported the calculated values were the same
- Automated test command result: `11 passed in 0.27s`
- Discrepancies and corrections: None reported
- Reviewer explanation in own words: Transaction costs are paid from the portfolio itself. Therefore, the sale must finance both the purchase and the trading cost. The amount sold is slightly larger than the amount bought by exactly the transaction cost. Equal buy and sell amounts would require an external cash contribution or a separate cash reserve.
- Reviewer initials/sign-off: KAD

After completion, copy the factual review outcome into `docs/final/01-planning/03-ai-use-log.md`. Do not claim that the whole investment strategy is human-validated; this check validates the portfolio accounting example only.
