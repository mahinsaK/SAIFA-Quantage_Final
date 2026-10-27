# EVT threshold-boundary support — 27 October 2026

Status: implementation and automated verification complete; **reviewer reported completing the new calculation and UI checks on 27 October 2026**. The review record below reflects the reviewer's confirmation; the earlier signed worksheet remains a separate historical record.

## What changed and why

The earlier implementation rejected confidence equal to `1 - N_u/n`. It now supports equality: `VaR=u`, `ES=u+beta/(1-xi)` when `xi<1`. This follows by substituting `p_u/(1-c)=1` into the documented POT formulas. The model uses the [SciPy GPD definition and support](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genpareto.html). The 90th-percentile threshold, fitting algorithm, frozen weights, data and random seeds did not change. This is an implementation-domain correction, not threshold tuning to obtain better backtests.

Boundary VaR is the empirical threshold, not tail extrapolation or independent corroboration of Historical VaR. ES remains a fitted GPD estimate and can differ from Historical ES. Confidence below the effective boundary remains unavailable. Ties can raise that boundary above the nominal threshold percentile. Failed/nonregular fits and infinite-mean ES keep their existing safeguards.

## Frozen-output evidence

Snapshot `20261023T102523Z-0d40a885`; as-of 2026-10-22; forecast session 2026-10-23; 1,000 observations; one session; fixed target exposures and USD 10 million reference NAV, before future trades or spending. These are not monthly performance losses or multi-day crisis drawdowns.

Run `uv run --locked python commands/run_app_data.py`, then `uv run --locked python commands/run_submission.py`. Neither downloads market data. The bundle identifies the exact run folders. For this configuration the risk folder is `output/evt/20261023T102523Z-0d40a885/b15d3b2b0378/`; backtests are under `output/backtest/20261023T102523Z-0d40a885/01664d7d6941/`.

| Portfolio | 90% VaR (USD) | 90% ES (USD) | Valid bootstrap draws / 200 |
|---|---:|---:|---:|
| 40/60 baseline | 51,173.71 | 80,286.96 | 124 |
| Minimum volatility | 52,693.88 | 81,963.42 | 125 |
| Maximum Sharpe | 53,315.23 | 83,281.36 | 111 |

All three selected fits have 100 strict exceedances and finite point estimates. **90% bootstrap intervals are withheld**: ties in resamples move the effective boundary above 90% in too many draws (more than 10% invalid). No replacement interval is manufactured. Read `interval_warning` in `evt_estimates.csv` alongside the estimate warning.

All 5,889 dated 90% EVT forecasts (1,963 sessions per portfolio) are available in this frozen run. This does not establish accuracy or safety. The following tests use validation and evaluation separately, with 5% significance:

| Portfolio / period | Exceptions / sessions | Kupiec p | Coverage | Independence p | Clustering |
|---|---:|---:|---|---:|---|
| Baseline / validation | 90 / 757 | 0.091491 | Do not reject | 0.081770 | Do not reject |
| Min volatility / validation | 91 / 757 | 0.071467 | Do not reject | 0.491543 | Do not reject |
| Max Sharpe / validation | 93 / 757 | 0.042233 | Reject | 0.604851 | Do not reject |
| Baseline / evaluation | 124 / 1,206 | 0.745178 | Do not reject | 0.007476 | Reject |
| Min volatility / evaluation | 149 / 1,206 | 0.008303 | Reject | 0.141965 | Do not reject |
| Max Sharpe / evaluation | 152 / 1,206 | 0.003624 | Reject | 0.311571 | Do not reject |

At the boundary these VaR exception sequences match Historical VaR. They are not two independent model successes. Basel traffic lights remain restricted to complete 250-session 99% windows; no 90% colour is manufactured.

Regression comparison against the pre-change saved CSVs: all 24 selected 95%/99% risk rows and all 47,112 95%/99% forecast rows have unchanged values. The forecast exception column now loads as integer rather than floating point because the previously missing 90% exceptions are available.

Automated verification: 212 full-suite tests passed; Ruff lint passed. New checks cover the exact boundary against SciPy, continuity, below-domain/tied samples, infinite ES, unavailable bootstrap intervals, USD conversion, past-only forecasts, selectable available and genuinely unavailable app states, and date-range recalculation. The original failed backtests remain visible. Frozen-snapshot Streamlit AppTest rendered all five pages without exceptions; all nine EVT portfolio/confidence selections matched CSV USD values. The existing local server health endpoint returned `ok`. Browser automation was not used and visual browser acceptance remains a human task. The regenerated 12-page report, one-page tear sheet and one-page memo passed artifact/source hash verification; all pages were rendered for a contact-sheet inspection and the changed report/tear-sheet pages inspected at readable size. Automated checks do not replace the review below.

## New manual review — reviewer record

1. With the artificial worksheet inputs `u=0.02`, `beta=0.01`, `xi=0.2`, 100 exceedances / 1,000, and confidence 90%, calculate `VaR=0.02` and `ES=0.02+0.01/0.8=0.0325`. At USD 10m these are USD 200,000 and USD 325,000. These are example values, not fund estimates.
2. Change `xi` to zero: VaR remains 2%; ES becomes 3%, USD 300,000. If `xi>=1`, ES is unavailable.
3. Suppose ties leave only 50 exceedances: the effective boundary is 95%. Explain why 90% stays unavailable and 95% can use the boundary formula. This does not change the configured quantile.
4. In `evt_estimates.csv`, select baseline 90%. Check `var_fraction=threshold`, `es_fraction=threshold+scale/(1-shape)`, and USD values equal fractions times 10m. Compare the first table above. Inspect the bootstrap valid counts and interval warning.
5. Refresh the local app, select Risk comparison, EVT POT/GPD and 90%. Check the same values and the boundary explanation. Switch to 95% and 99% and verify the displayed values change.
6. On Backtesting select 90% EVT and the full evaluation interval 2022-01-03 to 2026-10-22. Check exceptions and tests against the evaluation rows above. Shorten the range: observations/statistics must recompute. Check the absence of a Basel colour at 90% and read the rejection warnings.
7. Explain in your own words why empirical boundary VaR and fitted tail ES are different, and why the new estimates do not resolve failed backtests or establish suitability for the fund.

- Reviewer and date: Mahinsa Kuruppu, 27 October 2026.
- Calculator/spreadsheet and arithmetic results: Calculator. Reviewer reported the example checks matched: at the 90% boundary, `u=2%`, `beta=1%`, `xi=0.2` gives VaR 2% (USD 200,000) and ES 3.25% (USD 325,000) on USD 10 million. With `xi=0`, ES is 3% (USD 300,000); with `xi>=1`, no finite ES is reported. If ties leave 50 strict exceedances out of 1,000, the effective boundary is 95%, so a 90% EVT estimate is unavailable for that sample.
- Snapshot/run folders and app figures checked: Reviewer confirmed the frozen snapshot and app figures matched the displayed results. The baseline 90% risk CSV has `threshold=var_fraction=0.0051173705026037021`, `shape=0.073661453522635895`, and `scale=0.0026968730870056798`. Thus `ES=threshold+scale/(1-shape)=0.0080286960619914867`. Multiplying by USD 10 million gives VaR USD 51,173.71 and ES USD 80,286.96 after rounding. The 90% bootstrap has 124/200 valid baseline draws, so its confidence intervals are withheld; the other portfolios have 125/200 and 111/200 valid draws. Reviewer reported the app's 90% boundary explanation and distinct 95%/99% values were checked.
- Date ranges and statistics checked: Reviewer reported the Backtesting page checks were fine. The full evaluation range is 3 January 2022 through 22 October 2026 (1,206 sessions). At 90% EVT, baseline has 124 exceptions: Kupiec p=0.745178 (do not reject coverage) and Christoffersen p=0.007476 (reject independence). Minimum volatility has 149 exceptions and rejects coverage (p=0.008303); maximum Sharpe has 152 and rejects coverage (p=0.003624). Basel traffic lights are inapplicable at 90%. Reviewer reported that changing the selected range updated the display; the exact shorter range and its figures were not recorded here.
- Interpretation of boundary, missing intervals and failed backtests: At the effective boundary, VaR is the observed loss cutoff; ES estimates the average loss beyond it from the fitted GPD. They answer different questions, and the 90% EVT VaR is not independent evidence from Historical VaR. Tied bootstrap samples can shift the effective boundary and leave too few valid draws for a reliable interval. Available point estimates do not remove the observed coverage and clustering failures or establish that the model is suitable for the fund. This wording is a prepared summary of the checks the reviewer said were satisfactory.
- Discrepancies/corrections: None reported by the reviewer for this manual check. The earlier software boundary exclusion is documented above as a separate correction.
- Decision/sign-off: KAD (entered by reviewer). This signs off the reported worksheet checks, not client approval of the threshold, risk policy, investment allocation, or future model performance.
