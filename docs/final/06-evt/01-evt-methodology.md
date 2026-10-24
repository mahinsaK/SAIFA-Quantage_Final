# EVT methodology: peaks over a loss threshold

Implemented research model. The named reviewer completed manual arithmetic and retained the 90% threshold provisionally; out-of-sample coverage remains a separate check.

## Inputs and timing

Use the same three frozen target allocations, aligned simple returns, one-session horizon and USD 10m reference NAV as the earlier risk comparison. Portfolio loss is `L = -(returns @ weights)`; positive means loss. We do not average individual ETF VaRs. There is no trade, fee or withdrawal during the scenario.

`run_evt.py` rebuilds the data outputs offline from the verified snapshot and fits portfolio weights using development data ending before 2019-01-01. It uses only observations through the requested as-of close. The default current window has 1,000 returns. The independent development diagnostic panel ends on 2018-12-31. Estimates forecast the next exchange session, not the already observed as-of session.

The final-period performance has already been seen in earlier milestones. These are retrospective research diagnostics, not a claim of a fresh untouched test set. Changing a threshold after viewing current-period results must be disclosed, even if the code prevents future observations entering a particular fit.

## Threshold rule and its justification

The default rule is fixed at the empirical 90th loss percentile, using the inverse empirical CDF (`inverted_cdf`). Use strict exceedances `L > u`, so ties at `u` do not enter the GPD sample. The observed count, not a theoretical 10%, determines the exceedance probability.

At 1,000 distinct observations, 90% supplies 100 excesses, versus 50 at 95% and 25 at 97.5%. This balances tail focus with fitting information and keeps the threshold below both forecast levels (95% and 99%). The chosen minimum of 50 exceedances is a research guard, not a theorem guaranteeing accuracy. A successful fit is also not evidence that the GPD approximation is adequate.

The fixed diagnostic grid is 80%, 85%, 90%, 92.5%, 95%, 97.5%. The lower levels help expose body-distribution contamination; higher levels expose sampling instability. For each allocation and period, outputs include:

- Mean excess versus actual loss threshold: look for an approximately linear region.
- Shape and modified scale `beta - xi*u` versus threshold: approximate stability supports the tail approximation.
- Strict exceedance count and fit status.
- Selected-threshold GPD Q-Q points and plot: systematic deviations matter, especially at the largest losses.
- VaR/ES sensitivity across the grid; unavailable cells remain blank with reasons.

No automatic procedure chooses the threshold with the lowest risk or best final-period backtest. Development diagnostics support review of the prespecified rule; current-window diagnostics describe sensitivity. The team must record its reasoning in the [manual EVT check](03-manual-evt-check.md). The default is a defensible candidate, not an asserted optimal threshold. The actual development shape estimates vary across the grid, particularly for optimized portfolios, so stability is imperfect and must be acknowledged.

At default settings, 90% *forecast confidence* is not supported: it is at the threshold boundary. Return `below_tail_domain` rather than extrapolating the tail model into the body. A future app must show this explanation. A lower threshold can be researched explicitly, but requires its own justification.

## GPD fitting and risk formulas

Excess `Y = L-u` is modelled by a Generalized Pareto Distribution (GPD), with shape `xi`, positive scale `beta`, and location fixed at zero. For `xi != 0`, its survival is `(1 + xi*y/beta)^(-1/xi)` on its valid support. At `xi=0` it is exponential. See [SciPy's GPD definition and support](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.genpareto.html).

Fit by maximum likelihood using SciPy, with excesses scaled by their mean for numerical conditioning. The optimizer must report convergence, and parameters, support and log densities must be finite. Fits with fewer than three distinct excesses fail explicitly. Estimates with `xi <= -0.5` are withheld as nonregular MLE cases. This conservative guard can suppress a real bounded tail; it does not mean negative shape is always invalid. No optimizer fallback silently substitutes a Normal model.

Let `p_u = N_u/n` be the fraction of strict exceedances and `c > 1-p_u` the forecast confidence. Solving `P(L > VaR_c) = 1-c` gives:

```text
xi != 0: VaR_c = u + beta/xi * ((p_u/(1-c))^xi - 1)
xi == 0: VaR_c = u + beta * ln(p_u/(1-c))
xi < 1:  ES_c  = (VaR_c + beta - xi*u)/(1-xi)
xi >= 1: ES_c  has no finite model value
```

The implementation uses `expm1` for numerical stability and the exponential limit near zero. ES follows by adding the conditional mean GPD excess beyond VaR. A negative shape has a finite endpoint `u-beta/xi`. The theoretical GPD is not bounded by the long-only portfolio's maximum loss; estimates above 100% are flagged rather than clipped. Percent = decimal loss × 100; USD = decimal loss × reference NAV.

## Uncertainty

Default: 200 circular moving-block bootstrap resamples, blocks of 10 consecutive sessions, PCG64 seed 314159. Resample the entire ordered portfolio-loss series; recompute `u`, exceedance count and fit each time. Circular wraparound is intentional. All allocations use the same resample-index sequence for comparable scenarios. The portfolio weights, threshold quantile rule and other settings remain fixed.

The 2.5th/97.5th percentiles give nominal 95% intervals for VaR, ES, shape and scale. Raw draws and valid counts are saved. More than 10% unavailable VaR draws suppress intervals. Remaining intervals are explicitly conditional on successful fits when any draw fails. If a valid VaR draw has an infinite/nonfinite ES, withhold the ES interval rather than silently discarding that draw. A point estimate must exist to report its interval.

These intervals measure sampling variability under the chosen resampling assumptions. They are not predictive loss intervals, evidence of calibrated VaR coverage, or uncertainty in the choice of model/weights. Ten-session blocks preserve some short dependence, but do not establish stationarity or cover long regimes. The 200-replicate endpoints are relatively coarse. Use `--block-length 5` and `--block-length 20` for additional uncertainty sensitivity if it becomes material to the recommendation.

## Outputs and reproduction

```bash
uv run --locked python run_evt.py
uv run --locked pytest tests/test_evt.py -q
uv run --locked pytest -q
uv run --locked ruff check .
```

Outputs: `output/evt/<snapshot>/<settings-hash>/`. Only use a run whose `status.json` says `complete`. Here, complete means the pipeline ran; read individual estimate statuses before using numbers.

| File | Meaning |
|---|---|
| `evt_estimates.csv` | Selected-rule estimates, percent/USD, intervals, counts and warnings |
| `risk_comparison.csv` | Historical, Normal, Gaussian MC and EVT on identical inputs (24 rows by default) |
| `threshold_diagnostics.csv` | Development/as-of thresholds, parameters, counts and fit statuses |
| `threshold_sensitivity.csv` | Tail estimates for every grid threshold and confidence |
| `qq_diagnostics.csv` | Sorted observed excesses and fitted GPD quantiles |
| `bootstrap_draws.csv` | Raw resampling results, including unavailable cases |
| `diagnostics_*.png` | Six charts: three allocations × two periods |
| `portfolio_weights.csv`, `estimation_returns.csv` | Exact exposures and current fit inputs |
| `evt_report.md` | Results, rationale, uncertainty and limitations |
| `summary.json` | Config, timing, dependency/code/output hashes and review status |

Settings changes create different folders; identical settings reproduce outputs in the same environment. Model code updates are recorded through source hashes. Machine outputs never claim human approval automatically; the named worksheet is the human record.

## Remaining validation

Human arithmetic and provisional threshold interpretation are recorded in the [manual EVT check](03-manual-evt-check.md). Walk-forward forecast coverage, independence, stress-period behaviour and a final allocation recommendation remain separate milestones. This unconditional EVT model has no volatility filter or declustering. It should not be assumed to outperform empirical or Normal risk models merely because it models extremes.
