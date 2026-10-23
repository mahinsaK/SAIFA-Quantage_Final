# One-day VaR and Expected Shortfall methodology

Research implementation; human review is recorded separately in [manual-risk-check.md](manual-risk-check.md).

## What is being compared

Three allocations: exactly 40% SPY / 60% AGG, minimum-volatility target weights, and maximum-Sharpe target weights. Optimized weights are reproduced from development data ending 31 December 2018 using the existing policy and estimator. We do not optimize again on the risk window. All seven ETFs remain in the input matrix, including any zero-weight holdings.

Each allocation is valued at the same hypothetical **USD 10 million** for comparison. This is target-allocation risk, not the risk of drifted holdings or the actual ending wealth in the earlier performance backtest. Change the reference NAV with `--nav`; percentage estimates remain unchanged and dollars scale linearly.

The exposure is held fixed for **one trading session**, without a trade during the scenario. All three methods estimate market P&L before any future transaction cost. Previously implemented historical strategy accounting continues to include opening and rebalancing costs. These risk estimates must not be described as total net-of-cost strategy-loss forecasts.

## Information timing and sample

Default as-of date is the last observed close in the selected immutable snapshot. Use the last **1,000 observed daily simple-return rows through that date**, inclusive, and forecast the following XNYS session. A request for a holiday, a missing date, fewer than the requested observations, or an as-of date before portfolio estimation finished fails explicitly. No future return enters the model window, and no missing observation is filled.

The 1,000-session window is a declared research default, not a calibrated optimum. It gives roughly four years of observations and ten effective observations in a 1% historical tail. The library supports 90% confidence for the future interface; the default report contains 95% and 99%. Different settings have separate output directories. Window sensitivity remains a task for development/validation, before selecting final risk-model settings.

This milestone produces an as-of estimate, **not a VaR coverage backtest**. Forward-looking indexing alone does not establish calibration. The earlier full-period performance results have already been inspected, so we cannot claim a newly untouched holdout. Walk-forward forecasts and realized losses, Kupiec, Christoffersen and traffic-light evidence remain outstanding. Source revisions and estimated weights retain the limitations documented in the data and optimisation methodology.

## Loss convention and empirical tail

For asset simple returns `r` and weights `w`, portfolio return is `w @ r`, loss fraction `L = -(w @ r)`, and dollar loss is `NAV * L`. A positive loss is a fall in wealth. Negative VaR/ES values are permitted: they represent gains at the relevant threshold/tail and are not silently clipped. A decimal fraction `0.01` is **1%**, not 0.01%.

Although log returns are supplied for statistical diagnostics, simple returns are used here because one-day P&L of fixed linear ETF holdings is exactly a weighted sum of asset simple returns. A weighted sum of asset log returns would not give that same P&L. No square-root-of-time scaling or annualisation is applied.

Historical simulation keeps each complete seven-asset return row together, preserving observed cross-asset dependence. VaR is the smallest empirical loss whose cumulative probability reaches the chosen confidence: NumPy's `method="inverted_cdf"`. For sorted ascending losses `L[1], ..., L[n]`, this is rank `ceil(n*c)`.

ES is the average of the worst `(1-c)` probability mass, equivalently the integral of the empirical loss quantile from `c` to 1 divided by `(1-c)`. We take the worst `n*(1-c)` observations, using a fractional observation at the boundary if necessary. This definition handles ties. Simply averaging every value `>= VaR` can include too much probability mass and give a different answer for a discrete sample.

## Parametric Normal and Monte Carlo

Fit daily arithmetic asset means `mu` and sample covariance `Sigma` with denominator `n-1` from exactly the same window:

```text
portfolio mean m = w' mu
portfolio volatility s = sqrt(w' Sigma w)
z = standard Normal inverse CDF at confidence c
VaR = -m + s*z
ES  = -m + s*standard_Normal_density(z)/(1-c)
```

Zero volatility produces deterministic loss `-m` for both estimates. Neither measure is a guaranteed loss ceiling.

Monte Carlo generates 200,000 **correlated multivariate Normal** asset-return scenarios from the same means and covariance. An eigenvalue square root supports singular sample covariance, including perfectly offsetting assets. Only negative eigenvalues attributable to numerical round-off are clipped; an invalid covariance fails. A local explicit PCG64 generator with seed 42 makes the output reproducible with the locked environment. All portfolios receive the same joint asset scenarios. The same empirical VaR/ES definitions are then applied to simulated losses.

Since a fixed linear portfolio of Normal asset returns is Normal, Monte Carlo should approach the Parametric result. Agreement is expected, not evidence that tails are correctly modelled. We report their differences and approximate conditional Monte Carlo standard errors for VaR and ES. These standard errors exclude parameter, historical-sampling and model uncertainty. Historical estimates can differ because observed skewness/tail shape is not imposed by a Normal fit; the sign or size of that difference is not assumed in advance.

Gaussian simple returns are unbounded and can theoretically imply losses above 100%. We do not censor them, which would silently change the distribution. Simulated portfolio occurrences are flagged. Normality and constant moments omit fat tails and volatility clustering. Historical simulation cannot extrapolate beyond observed events. Fewer than 20 effective historical tail observations or 100 simulated tail observations are visibly flagged as research heuristics, not regulatory thresholds.

## Files and reproduction

```bash
uv run --locked python run_risk.py
uv run --locked python run_risk.py --as-of 2026-10-22 --lookback 1000 --confidence 0.90 0.95 0.99
uv run --locked pytest tests/test_risk.py -q
```

The command rebuilds data from the verified snapshot without downloading and fits target allocations through the shared development-only estimator. It does not run the performance backtest, write its outputs or require observations from its validation/evaluation periods. Only development-period risk-free returns are used to estimate allocations; they must align with the development asset returns and use the same configured annualisation. Risk outputs are stored in `output/risk/<snapshot-id>/<settings-hash>/`:

| File | Purpose |
|---|---|
| `risk_report.md` | Portfolio/method comparison, observed differences and limitations |
| `risk_estimates.csv` | Each estimate in fraction, percent and USD; confidence, timing, tail counts and warnings |
| `portfolio_weights.csv` | Exact target weights used by all methods |
| `estimation_returns.csv` | Exact window of joint daily ETF simple returns |
| `asset_means.csv`, `asset_covariance.csv` | Daily moments fitted to that window |
| `summary.json` | Settings, dates, packages, Git state, source/input/output hashes and human-review status |
| `status.json` | Building, complete or failed state; always check before consuming results |

The same request replaces its reproducible outputs; different windows, seeds, confidence levels or NAV create different settings directories. Failed reruns can leave old artifacts, so consumers must require `status.json` to be `complete`. The settings hash identifies a request, not immutable output content; `summary.json` records content hashes. Generated outputs remain ignored by Git.

| Source | Responsibility |
|---|---|
| `src/domain/config.py`, `src/domain/risk.py` | Validated settings and typed results |
| `src/models/risk.py` | Window selection, portfolio exposure, distribution fitting, VaR/ES and simulation |
| `src/models/optimisation.py` | Shared development-only allocation fit, used by both risk and performance pipelines |
| `src/application/risk_pipeline.py` | Inputs, provenance, orchestration and outputs |
| `src/reporting/risk.py` | Markdown report content |
| `run_risk.py` | Command-line options |
| `tests/test_risk.py` | Hand examples, invariants, dependence, simulation convergence and integration checks |

## Definition references

- [NumPy quantile documentation](https://numpy.org/doc/2.0/reference/generated/numpy.quantile.html): explicit inverse-CDF quantile convention.
- [MathWorks Expected Shortfall example](https://www.mathworks.com/help/risk/estimate-expected-shortfall-with-the-expectedShortfall-function.html): analytical Normal ES and its tail interpretation.
