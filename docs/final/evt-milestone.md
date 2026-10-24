# EVT implementation milestone

Implemented 24 October 2026. Mahinsa Kuruppu completed the manual arithmetic and signed off the 90% threshold as a provisional research choice on 24 October 2026. Forecast coverage validation remains pending.

Default snapshot: `20261023T102523Z-0d40a885`. Settings run: `5feb6a842858`.
As-of close: 2026-10-22. Next session: 2026-10-23. Current window: 2022-10-27 through 2026-10-22, 1,000 observations. Development diagnostics: 2004-11-19 through 2018-12-31, 3,552 observations.

## Observed default results

The 90% loss-threshold rule supplies 100 current-window excesses for each allocation. All six selected VaR/ES estimates are finite. All 200 bootstrap replicates per allocation/confidence produced finite risk values in this run.

| Portfolio | 99% EVT VaR (%) | 99% EVT ES (%) | 95% bootstrap interval for 99% ES (%) |
|---|---:|---:|---:|
| 40/60 baseline | 1.1885 | 1.5334 | 1.1663–2.0083 |
| Minimum volatility | 1.2022 | 1.5038 | 1.2223–1.7236 |
| Maximum Sharpe | 1.2226 | 1.5184 | 1.2363–1.7335 |

These are research estimates, not guaranteed limits. Intervals are conditional on the chosen model, fixed allocation and resampling assumptions.

## Threshold evidence and limits

Development baseline shape estimates at 85%, 90%, 92.5% are approximately 0.2515, 0.2162, 0.2722. The baseline's estimated 99% VaR is relatively stable across this area, while parameters and ES vary. Optimized development shape estimates rise at the highest thresholds, so there is no basis to claim perfect parameter stability. Q-Q plots show departures in the largest observations. The named reviewer retained the default as a provisional sample-size/tail-focus compromise, with these limitations recorded.

The current 97.5% threshold leaves only 25 excesses and is withheld. At 95% confidence, thresholds at/above the effective 95% boundary are unsupported. Neither condition is silently replaced with a usable-looking number. The current-window evidence is not used to tune the default rule.

## Reproduction and review

See [methodology](evt-methodology.md) for formulas, provenance, bootstrap caveats and file definitions. The completed [manual worksheet](manual-evt-check.md) records independent arithmetic and threshold reasoning. Run `uv run --locked python run_evt.py` to reproduce the report, six diagnostic charts and all supporting CSVs. The runner verifies snapshot integrity and records dependency, code and output hashes.

Automated verification covers analytic GPD/exponential identities, known-distribution recovery, units/translation, ties, support limits, insufficient/degenerate/failed fits, infinite ES, block structure, repeatability and future-data isolation. See the final validation record below for the executed results.

R04 now has implementation and named human-review evidence. The subsequent [backtesting milestone](backtesting-milestone.md) implements walk-forward coverage/independence tests and records their rejections; human interpretation remains pending. Stress analysis and the committee decision remain outstanding. The threshold decision is provisional and must be revisited if forecasting evidence is poor, without tuning the already-viewed evaluation sample to pass.

## Executed validation record — 24 October 2026

- Focused EVT suite: **24 passed**. Full project suite: **93 passed**.
- Extended pipeline regression for 90% confidence: passed; unsupported EVT values and intervals remain blank with `below_tail_domain`, while other methods are retained.
- Ruff: passed. `git diff --check`: passed.
- Frozen default runner: completed. Counts verified: 6 EVT estimates, 24 comparison rows, 36 diagnostic rows, 72 sensitivity rows and 1,200 bootstrap rows.
- Two unchanged default runs: **all 17 output files byte-identical**, including charts and metadata. All recorded output hashes verified.
- Existing 18 Historical/Normal/Gaussian-MC estimate values are exactly equal to the earlier risk run.
- Generated baseline development/as-of charts inspected visually for readable axes and layout. Mean excess is plotted against the loss threshold (not percentile), as required for interpreting linearity.

These were assistant-executed checks. The team later completed and signed the separate manual worksheet.
