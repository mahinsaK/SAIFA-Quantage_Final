# Walk-forward VaR backtesting milestone

Implemented 24 October 2026. Human review of the arithmetic and interpretation remains pending in [manual-backtest-check.md](03-manual-backtest-check.md).

Snapshot: `20261023T102523Z-0d40a885`. Settings run: `93efaf13a75a`. Run `uv run --locked python commands/run_backtest.py` and read the printed `backtest_report.md`. Full assumptions and primary references are in [backtesting-methodology.md](01-backtesting-methodology.md).

## Frozen run

- 1,963 forecast sessions: 2 January 2019–22 October 2026. Validation has 757 sessions; evaluation has 1,206.
- Three fixed target allocations, four methods, two confidence levels: **47,112 forecast rows**. All default forecasts have finite VaR and ES; no missing fits in this run. Unsupported/custom configurations still preserve explicit unavailable rows.
- Each forecast uses 1,000 earlier returns, ending before its target date. The first window is 12 January 2015–31 December 2018. Optimised weights use development inputs ending 31 December 2018.
- 48 separate-period model/confidence summaries; 23,556 rolling 99% Basel rows, including early insufficient windows; 24 latest-window rows; six charts.
- Fixed USD 10m one-session exposure, no fees, NAV compounding or monthly weight drift. These losses are not the realised net-return series of the earlier strategy performance backtest.

## Findings that must remain visible

At the 5% level, validation has 15/24 coverage rejections and 10/24 independence rejections. Evaluation has 8/24 coverage rejections and 4/24 independence rejections. These are descriptive counts across related tests, not a multiple-testing-adjusted model ranking. Many independence results have sparse expected transition cells, so asymptotic p-values require caution.

For baseline Historical 99% VaR during evaluation, there are **11 exceptions versus 12.06 expected**. Kupiec p is approximately **0.7555**, while Christoffersen independence p is approximately **0.002892**. The overall frequency alone therefore misses clustering. Baseline 99% independence is rejected for all four methods in this period.

The evaluation period's minimum-volatility and maximum-Sharpe Normal/Monte Carlo 99% forecasts each have **22 exceptions versus 12.06 expected**, with Kupiec p approximately **0.009896**. This suggests undercoverage over that sample. EVT has nine exceptions for each of those allocations and neither of its 99% tests rejects, but this does not establish EVT as universally superior or safe; its 95% coverage is rejected for those allocations, and tail-fit/finite-sample limitations remain.

The latest 250-session evaluation window is 24 October 2025–22 October 2026. Baseline counts are one for Historical/Normal/Monte Carlo and zero for EVT: all green. Optimised allocations have six for Historical/Normal/Monte Carlo (yellow) and four for EVT (green). Earlier rolling windows include red zones. A final green colour must not be used to conceal earlier failures or replace the full-period tests.

No automatic model selection, window tuning or threshold adjustment was performed. The original 90% EVT quantile rule remains provisional. Use the evidence in stress analysis and investment interpretation; any later research refinement should document the changed hypothesis and use fresh evaluation evidence where possible. Prior final-period performance was already viewed, so the evaluation remains retrospective.

## Executed automated verification

- Focused backtesting suite: **30 passed**. Full project suite: **123 passed**. Ruff passed.
- Hand-example likelihoods and transition counts; zero/all-exception limits; equal-rate sequences with different clustering; sparse/missing-data unavailability; exact Basel boundaries.
- Holiday-aware previous-session timing, missing calendar dates rejected, strict loss/VaR equality, USD scaling and covariance preservation.
- Changing a target return changes its realised loss but not its forecast; later returns/rates cannot affect earlier forecasts or development weights. Shared-date forecasts remain unchanged when the selected start date or portfolio order changes.
- Pipeline regression includes unavailable EVT fits, separate periods, metadata, failed-run status and byte-for-byte repeatability on deterministic test data.
- Full default runner completed and observed counts/results checked. Baseline evaluation plot inspected for readable axes, dates and exception markers.

- Two unchanged full-data reruns produced **15 byte-identical output files**, including metadata and charts. All 13 recorded output hashes and 32 Python source hashes were checked against the files.
- Independently checked all 47,112 exception flags against the saved loss/VaR columns, origin-before-target ordering, 1,000-observation windows and 1,963 rows per portfolio/model/confidence group.
- Rolling Basel status counts: 17,580 complete windows and 5,976 insufficient early windows; early windows receive no invented colour.
- `git diff --check` passed. Generated outputs remain ignored by Git and are reproduced by the runner.

Automated verification establishes implementation evidence, not named human sign-off or investment suitability.
