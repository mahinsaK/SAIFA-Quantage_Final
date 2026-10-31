# Research lab milestone and measured findings

31 October 2026. Snapshot `20261023T102523Z-0d40a885`. Human review pending; no client or scenario approval implied.

## Implemented evidence

- The Research lab scope expander now lists coverage and limits as text instead of a canvas-rendered data grid. Its rolling re-optimisation entry points to the implemented Portfolio → Annual strategy section; the former separate-PR label was stale. Missing client, payment-date, split-unit and execution inputs remain labelled as such.
- Five original pages retained; a separate **Research lab** sidebar page exposes six visible topics—allocations, stability, changing risk, spending, income and costs—with plain-language questions. The original sidebar's financial controls are hidden on this page and restored on return. Methodology expanders remain collapsed by default; table titles and CSV download labels describe their contents.
- Two alternative fits use the original development period and policy, then share the same validation/evaluation accounting. Original three evaluation NAVs reproduced with **zero numerical difference** in the frozen-data comparison.
- Seventy-four robustness rows: seven prespecified variants plus thirty block resamples for each of two objectives. Failures have explicit unavailable rows.
- Twenty-four annual GARCH parameter fits converged on the snapshot. Dated GARCH Normal/FHS and EWMA forecasts span the original target sessions; parameter-fit and as-of dates are exported. Fifty-four new-model/portfolio/confidence/period checks contain **17 coverage rejections and 3 independence rejections**. Counts are overlapping diagnostics, not a model accuracy score or a direct comparison with a differently sized original-model grid.
- Eighteen conditional spending scenarios share a 54-month recent joint asset/CPI sample and gap-aware blocks; each has its own 121-point real-wealth quantile paths. Income limitations, fee sensitivity and lagged-volume evidence retain missing-input reasons.
- The spending view now places no-shortfall, preservation of initial real capital and the separate stricter 3% after-spending objective together. The changing-risk view recomputes every available method's checks on the same selected portfolio, confidence and dates. Income availability is visible across all five candidates; cost sensitivity shows basis-point conversions and USD differences against the 10 bps/no-extra-fee reference. These are presentation changes to verified outputs, not new financial estimates.

## Alternative allocation results

Evaluation: 3 January 2022–22 October 2026; each USD 10m initial capital, monthly rebalanced, 10 bps on gross buys/sells including funding, no withdrawals.

| Candidate | Ending NAV (USD) | Annual return | Annual volatility | Funded-NAV drawdown loss | Trading costs (USD) |
|---|---:|---:|---:|---:|---:|
| Original minimum volatility | 13,427,240.20 | 6.3327% | 8.0413% | 16.9620% | 21,877.95 |
| Original maximum Sharpe | 13,512,711.30 | 6.4734% | 8.1727% | 17.1857% | 22,325.67 |
| Minimum historical ES | 13,555,828.31 | 6.5441% | 8.1825% | 17.0430% | 22,464.08 |
| Constrained risk parity | 13,345,894.86 | 6.1982% | 7.7881% | 15.5110% | 21,948.23 |

Minimum ES has a lower development empirical 95% tail loss by its objective. It does not minimise evaluation volatility or drawdown; its evaluation drawdown exceeds original minimum volatility. Risk balancing has a different trade-off, not an automatic winner. Its maximum risk-share gap is approximately `0.001847` (0.1847 percentage points), so it is not flagged as exactly equal-risk at tolerance `1e-4`.

Validation ending NAVs: minimum ES **USD 14,046,484.78**, constrained risk parity **USD 13,529,836.01**. These results do not establish prospective calibration or committee suitability. Alternative-candidate crisis and forecasting studies remain separate.

## Spending and income interpretation

Baseline / 3% initial annual withdrawal / no extra inflation uplift: all 1,000 simulated paths paid scheduled spending, but only **63.5%** preserved initial real capital. Median terminal real wealth is **USD 11,093,950.38** and its 5th percentile **USD 6,710,948.00**. The conditional no-shortfall Wilson lower bound is **99.6173%**, not a forecast confidence bound. The short recent sample excludes earlier crises, so a 100% sample success frequency does not establish safety or ten-year sustainability. This simulation does not replace the earlier observed CPI/no-withdrawal assessment.

The SPY/AGG baseline constant-exposure distribution proxy is **USD 1,218,710.47** over the evaluation period. It is not actual fund cash income or a dividend forecast and must not be added to portfolio total returns. Complete totals for candidates exposed to the recorded XLE/XLK splits remain unavailable pending unit review; actual payment dates and tax treatment are missing for every candidate.

## Verification and limitations

- Focused model/loader/UI/launcher/navigation tests passed; after merging the Phase 11 annual experiment from current main, the combined full suite is **278 passed**. Ruff lint and format checks also pass.
- Tests include analytical ES bounds, equal-variance ERC, constrained non-equality, future-return perturbation, GARCH recursion and units, no silent forecast fallback, CPI gaps, first-payment indexing, exhaustion, conditional interval boundaries, full-rotation costs, fee homogeneity, prior-only volume, split-unavailable income, manifest integrity and control-dependent recalculation.
- Real-snapshot AppTest rendered all six visible topics without exceptions and verified the baseline 3% spending figures (100% no shortfall, 63.5% real-capital preservation, 23.8% stricter after-spending objective). The all-model table had five methods with 1,206 evaluation forecasts each; shortening the range to January 2022 recomputed every row to 20 forecasts. Loader validated the real 18-table bundle. Page-routing tests verify navigation into and out of Research lab and restoration of the original sidebar choices. No browser automation was used; desktop/mobile appearance and topic wrapping still need human acceptance.
- The combined frozen-snapshot launcher preparation rebuilt stale decision, PDF, annual and research artifacts successfully. Existing frozen submission PDFs are separate from this experiment. No new-package or fresh-clone installation test was repeated for the lab; it uses the project's existing locked packages and offline launcher.
- Final investment judgment, scenario approval, split-unit interpretation, spending suitability and remaining core worksheets stay open. See the [manual worksheet](03-manual-research-check.md).
