# Walk-forward VaR backtesting methodology

Implemented 24 October 2026. Human review is recorded separately in [manual-backtest-check.md](manual-backtest-check.md). This evaluates forecasting, not whether an allocation should be recommended to the client.

## Protocol and information timing

1. Verify the frozen snapshot and reproduce the prepared simple returns. Require all seven eligible ETFs and consecutive XNYS sessions, with no skipped dates or shorter training fallback.
2. Estimate the minimum-volatility and maximum-Sharpe target weights using development returns and aligned risk-free rates ending 31 December 2018. Keep these weights, and the 40% SPY / 60% AGG baseline, fixed throughout forecasting. Future returns or risk-free rates cannot change the weights.
3. At the close before each target session, use exactly the preceding 1,000 observed daily returns. The target day's return is excluded. For example, the first forecast is issued using data through 31 December 2018 for 2 January 2019; 1 January is an exchange holiday.
4. Fit all four prespecified models on the same window and portfolio: Historical, Parametric Normal, Monte Carlo Normal and EVT POT/GPD. Forecast 95% and 99% one-session VaR and ES.
5. Compare the forecast with the next observed session's signed portfolio loss. Store a row even when the EVT estimate is unavailable; do not remove difficult dates.
6. Evaluate 2019–2021 validation and 2022–22 October 2026 evaluation separately. The end date is exclusive in configuration. Rolling model estimates may use previously observed validation/evaluation returns, but never the forecast target or later returns. This is normal sequential updating, not a re-optimisation of portfolio weights.

The 1,000-observation window, 90% EVT threshold rule, 50 minimum excesses, 200,000 simulations, seed 42 and 5% test significance are retained research settings. No winning model or threshold is selected automatically from the backtest. Earlier final-period performance has already been viewed, so this is **retrospective evaluation**, not a claim of a newly untouched holdout. The adjusted-price snapshot is also a current data vintage, not a complete archive of point-in-time vendor revisions.

## Exposure and loss convention

For fixed target weights `w` and simple asset returns `r_t`:

```text
portfolio return_t = w' r_t
loss_t = -w' r_t
exception_t = 1 if loss_t > VaR forecast_t, otherwise 0
USD amount = loss or risk fraction × 10,000,000
percentage = fraction × 100
```

Equality is not an exception. A gain is a negative loss; do not clip it to zero. All forecasts use the same hypothetical USD 10m NAV. This is one-session risk for target exposures, not the actual monthly-rebalanced portfolio NAV: no compounding, transaction fees, drifted weights or withdrawals are included. The realised investment-strategy comparison remains in the portfolio/optimisation modules. These different purposes must stay labelled in the final app/report.

## Models

Historical uses the inverse empirical CDF and fractional probability mass for ES, as in [risk methodology](risk-methodology.md). Parametric Normal uses the portfolio's sample mean and sample standard deviation (`ddof=1`). Projecting the asset panel first preserves covariance: `Var(Rw) = w' Cov(R) w`.

Monte Carlo draws 200,000 standard Normal losses per target date, then applies `-mean + sigma × draw` for each portfolio. This has exactly the marginal distribution of the linear portfolio under a joint Gaussian asset model; it is a computational shortcut, not an independent distributional alternative to Parametric Normal. The same standard sample across portfolios is a numerical coupling and must not be used as a simulated joint distribution of different portfolios. Covariance within each portfolio is preserved.

The generator is PCG64 with `SeedSequence([42, target_date.toordinal()])`. Changing the selected start date or portfolio order cannot change a given date's draws. Monte Carlo results can differ slightly from analytical Normal results and from the earlier single-as-of risk runner's random realization. Both implementations retain their stated Gaussian assumptions.

EVT refits the numeric 90th-percentile loss threshold and GPD parameters from each historical window, while keeping the quantile-selection rule fixed. Ties use the actual strict-exceedance count. The confidence must be above the fitted tail boundary. Insufficient excesses, unsupported confidence, failed fits and undefined ES retain explicit statuses. A finite VaR remains testable when ES is unavailable because the fitted tail has no finite mean. See [EVT methodology](evt-methodology.md).

## Coverage: Kupiec

For `n` observations, `x` exceptions, confidence `c`, expected probability `p=1-c` and observed rate `q=x/n`:

```text
log L0 = (n-x) ln(1-p) + x ln(p)
log L1 = (n-x) ln(1-q) + x ln(q)
LRuc = 2 (log L1 - log L0)
p-value = P(chi-square with 1 degree of freedom >= LRuc)
```

Use the limit `0 ln(0) = 0` for zero/all-exception samples. Also report an exact two-sided binomial p-value. The chi-square decision uses the prespecified 5% significance level; the exact p-value is a finite-sample diagnostic, not a replacement chosen after seeing which result is favourable. Sparse/boundary counts carry warnings. Both tests rely on independence assumptions; the exact test does not solve clustering. An incomplete sequence has descriptive counts but unavailable inferential results.

## Clustering: Christoffersen independence

Count consecutive transitions `n00`, `n01`, `n10`, `n11`, with the previous exception state first. There are `n-1` transitions. Set:

```text
pi01 = n01 / (n00+n01)
pi11 = n11 / (n10+n11)
pi   = (n01+n11) / (n00+n01+n10+n11)
log L0 = (n00+n10) ln(1-pi) + (n01+n11) ln(pi)
log L1 = n00 ln(1-pi01) + n01 ln(pi01)
       + n10 ln(1-pi11) + n11 ln(pi11)
LRind = 2 (log L1-log L0)
p-value = P(chi-square with 1 degree of freedom >= LRind)
```

This conditions on the first observation and tests first-order independence; it is not the combined conditional-coverage test. Missing forecasts are never joined across a gap. Any missing forecast withholds the period's inferential test. At least five transitions from each previous state are required; this is a conservative research eligibility rule, not a theorem guaranteeing good asymptotics. Small expected transition cells still carry a caution. No/very few exceptions can therefore mean unavailable evidence, not a pass.

## Basel traffic light

Use the historical 99% / 250-consecutive-session convention: **0–4 green, 5–9 yellow, 10 or more red**. Generate every rolling window and a latest-window view for each period. Windows reset at the validation/evaluation boundary. Fewer than 250 sessions or any unavailable forecast means no colour. No colour is produced for 95% confidence, and no alternative thresholds are silently substituted.

The traffic light is a historical research diagnostic, not a statement that this endowment satisfies current bank capital regulation. A green latest window can coexist with an independence rejection over a longer period. Its thresholds and purpose differ from a two-sided Kupiec test; five exceptions can be yellow while Kupiec does not reject.

## Interpretation and outputs

Report both frequency and clustering, including failures. `do_not_reject` means insufficient evidence to reject that null at the chosen significance level, not model correctness. Tests have limited power, overlapping rolling windows are dependent, and no correction for the many reported tests is applied. These VaR tests do **not** validate ES severity forecasts. Rejection warrants investigation and stress analysis; do not remove crisis days or tune the evaluation period until it passes.

Run `uv run --locked python run_backtest.py`. Outputs are under `output/backtest/<snapshot>/<settings-hash>/`; identical settings reproduce the same folder. Require `status.json` to say `complete`.

| File | Purpose |
|---|---|
| `forecasts.csv` | Dated origins/windows/targets, weights cutoff, losses, VaR/ES in fractions/percent/USD, exceptions, fit statuses and seed dates |
| `test_summary.csv` | Separate-period coverage and independence statistics, counts, exact binomial diagnostic and warnings |
| `basel_rolling.csv`, `basel_latest.csv` | All rolling and latest 250-session diagnostics, including unavailable windows |
| `portfolio_weights.csv`, `returns_used.csv` | Fixed allocations and returns used in forecasting |
| `backtest_report.md`, six default PNGs | Readable comparison and loss/VaR plots with exceptions |
| `summary.json` | Configuration, Git state, source/dependency/output hashes, manifest and development-return hashes, scope and review record |
| `status.json` | Building, failed or complete; completion is not human sign-off |

Code map: `src/domain/config.py` holds settings; `src/domain/backtesting.py` holds typed records; `src/models/walk_forward.py` generates forecasts; `src/models/backtesting.py` calculates statistical tests; `src/application/backtest_pipeline.py` orchestrates and records provenance; `src/reporting/backtesting.py` renders results; `tests/test_backtesting.py` verifies timing, formulas, failures and repeatability. `run_backtest.py` is the entry point.

## Primary references

- [Kupiec (1995), Techniques for Verifying the Accuracy of Risk Measurement Models](https://fedinprint.org/item/fedgfe/34596/original).
- [Christoffersen (1998), Evaluating Interval Forecasts](https://users.ssc.wisc.edu/~behansen/718/Christoffersen1998.pdf).
- [Basel historical guidance, MAR99](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/99/inforce/2019-12-15/published/2019-12-15).
