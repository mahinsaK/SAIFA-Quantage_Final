# Portfolio optimisation milestone

Implemented and automatically verified: 23 October 2026. Human calculation and interpretation review is pending.

Snapshot: `20261023T102523Z-0d40a885`. Development estimates end on 31 December 2018; the final evaluation covers 3 January 2022 to 22 October 2026.

## Frozen candidates

| Strategy | SPY | AGG | GLD | XLK | Development return | Development volatility | Development Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|
| Minimum volatility | 14.27% | 60.00% | 18.08% | 7.64% | 5.98% | 6.03% | 0.78 |
| Maximum Sharpe | 12.15% | 60.00% | 17.85% | 10.00% | 6.03% | 6.04% | 0.79 |

EFA, EEM and XLE received zero weight in both solutions. Zero weights are solver results under these historical estimates and policy constraints, not claims that those assets are universally unsuitable.

## Out-of-sample evaluation with 10 bps costs

| Strategy | Ending value | Annualised return | Volatility | Maximum drawdown | Sharpe | Sortino | Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|
| 40/60 baseline | $12,448,401.99 | 4.67% | 8.53% | -18.78% | 0.10 | 0.14 | 0.25 |
| Minimum volatility | $13,427,240.20 | 6.33% | 8.04% | -16.96% | 0.29 | 0.42 | 0.38 |
| Maximum Sharpe | $13,512,711.30 | 6.47% | 8.17% | -17.19% | 0.31 | 0.44 | 0.38 |

Both candidates beat the baseline in this held-out historical period while showing lower volatility and a smaller drawdown. This is useful evidence but does not establish future superiority. The candidates are close because AGG reaches its 60% single-asset ceiling and both use substantial GLD; input sensitivity and the required risk models may change the final decision.

CAPM and remaining KPI values are in `performance_ratios.csv`. The efficient frontier, frozen weights, validation results, daily accounting and transactions are under `output/optimisation/20261023T102523Z-0d40a885/` and reproduce with `uv run --locked python run_optimisation.py`.

Complete [manual-optimisation-check.md](manual-optimisation-check.md) before human sign-off. Data flags separately require the review in [data-quality-review.md](data-quality-review.md).
