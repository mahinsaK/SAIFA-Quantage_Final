# Annual re-optimisation milestone

30 October 2026. Snapshot `20261023T102523Z-0d40a885`. Proposed research only; manual review pending.

The separate branch implements two annually fitted candidates, retains all three original frozen comparators, and exposes both comparison periods on Portfolio → Annual strategy. Sixteen annual target rows cover 2019–2026, two objectives per year. Daily paths, self-financing trade records, aggregate metrics and annual-minus-frozen differences are exported. There are two post-funding annual target changes per validation strategy and four per evaluation strategy, plus the usual month-end rebalances.

## Measured evaluation results

2022-01-03–2026-10-22; USD 10m starts, monthly target restoration plus annual changes where applicable, 10 bps on gross trading, no withdrawals.

| Candidate | Ending NAV (USD) | Annual return | Annual volatility | Funded-NAV max drawdown loss | Trading costs (USD) |
|---|---:|---:|---:|---:|---:|
| 40/60 baseline | 12,448,401.99 | 4.6689% | 8.5321% | 18.7826% | 18,152.96 |
| Frozen minimum volatility | 13,427,240.20 | 6.3327% | 8.0413% | 16.9620% | 21,877.95 |
| Annual minimum volatility | 13,249,723.84 | 6.0383% | 7.6304% | 16.5764% | 24,021.56 |
| Frozen maximum Sharpe | 13,512,711.30 | 6.4734% | 8.1727% | 17.1857% | 22,325.67 |
| Annual maximum Sharpe | 15,405,162.37 | 9.4212% | 9.0643% | 17.2546% | 29,739.17 |

Annual maximum Sharpe increased measured evaluation ending wealth, volatility and trading costs. Annual minimum volatility reduced evaluation volatility/drawdown but also reduced ending wealth and increased costs. Neither is a universal improvement.

Validation ending NAVs are USD 13,295,382.28 annual minimum volatility versus USD 13,965,610.10 frozen, and USD 14,080,588.65 annual maximum Sharpe versus USD 14,104,756.84 frozen. Both annual candidates underperformed their frozen counterparts in validation ending wealth. Choosing only the favourable later result would omit relevant evidence.

The annual rule also changes estimation history relative to the original full-development frozen fits. No causal claim about update frequency alone, unviewed holdout performance, future superiority, adaptive risk calibration or client suitability follows from these results.

## Verification

- Focused accounting/model/pipeline/launcher/dashboard tests: **65 passed**.
- Full suite: **245 passed**; Ruff lint and formatting pass.
- Tests include strict temporal exclusion, perturbing future returns/rates, policy limits, missing history/rates, solver failure, roundoff normalisation, full-rotation funding with fees, duplicate/coincident events, preservation of fixed-target behaviour, output tampering, stale sources, period/objective controls and navigation anchors.
- The real frozen dataset produced all outputs with no downloads. Original frozen evaluation NAV differences were exactly zero in the reproduction check.
- Real-snapshot AppTest rendered all five pages without exceptions and checked both annual period/objective controls and the section anchor. The one-command preparation function refreshed and verified its outputs; existing report/tear-sheet/memo content stayed byte-identical with valid manifest bindings.
- Human comparison/interpretation, responsive browser appearance and any decision to promote this experiment remain pending in the [worksheet](03-manual-adaptive-check.md).
