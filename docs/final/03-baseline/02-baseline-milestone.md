# 40/60 baseline milestone

Implemented and automatically verified: 23 October 2026. Mahinsa Kuruppu subsequently completed the manual accounting check using a calculator and paper. All values matched, and the portfolio test command returned 11 passed in 0.27s.

Source snapshot: `20261023T102523Z-0d40a885`. Period: 18 November 2004 to 22 October 2026, 5,516 price observations. Initial capital: USD 10 million.

## Observed comparison

| Strategy | Ending value | Cumulative return | Annualised return | Annualised volatility | Maximum drawdown | Direct transaction cost |
|---|---:|---:|---:|---:|---:|---:|
| Buy-and-hold, no cost | $49,745,303.12 | 397.45% | 7.59% | 9.54% | -23.09% | $0.00 |
| Monthly 40/60, no cost | $38,265,355.08 | 282.65% | 6.31% | 8.02% | -23.72% | $0.00 |
| Monthly 40/60, 10 bps | $38,072,059.22 | 280.72% | 6.29% | 8.02% | -23.75% | $89,635.42 |

There were 263 complete month-end rebalances per monthly strategy. The 10 bps strategy's ending value was $193,295.86 below the no-cost monthly strategy; this difference includes direct costs and lost subsequent growth on money paid as costs.

Buy-and-hold finished higher in this realised period because the weights were allowed to drift rather than remain at the conservative 40/60 target. It also had higher annualised volatility. Its slightly smaller measured maximum drawdown does not prove it was safer or will outperform later. These full-sample results cannot select the final allocation and are not out-of-sample evidence.

## Verification completed

- 32 automated tests passed across the data and portfolio modules.
- Static checks passed.
- The cost solver passed pre-NAV = post-NAV + cost and net trades = negative cost for all scheduled transaction rows.
- All monthly post-trade weights equal 40% SPY / 60% AGG within numerical tolerance.
- The buy-and-hold ending NAV independently matched the closed-form holding-value calculation.
- The incomplete October 2026 month was not rebalanced.
- All seven generated portfolio output files were byte-identical on a second offline run.

Generated evidence is under `output/portfolio/20261023T102523Z-0d40a885/` and is reproducible with `uv run --locked python commands/run_portfolio.py`. The generated directory is intentionally ignored by Git.

## Human accounting validation

The completed calculation result, reviewer explanation and sign-off are recorded in [manual-accounting-check.md](03-manual-accounting-check.md) and [ai-use-log.md](../01-planning/03-ai-use-log.md). Generated `summary.json` and `status.json` remain conservatively marked pending because the script cannot infer or certify a human review.

This review validates the accounting example only. Data-quality flags, assumptions, investment suitability and future Markowitz/CAPM/risk-model work require their own reviews.
