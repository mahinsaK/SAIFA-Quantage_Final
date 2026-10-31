# Portfolio research lab methodology

31 October 2026. Retrospective experimental extension, using snapshot `20261023T102523Z-0d40a885`. No new market data, paid data source or dependency is introduced. Human interpretation and investment approval remain separate.

## Scope and research coverage

The five original pages and three frozen candidates remain the submission reference. A separate **Research lab** sidebar page exposes six optional panels with their own controls and collapsed explanations. Its scope expander uses readable text for the completed experiments and their limits; it is not an app setup checklist. The original portfolio/risk sidebar selectors are hidden on Research lab and retain their session choices when the user returns to those pages. Alternative allocations are not silently added to the main VaR/stress/spending selectors or committee recommendation.

| Requested direction | Implemented here | What is not established |
|---|---|---|
| Rolling weight re-optimisation | Phase 11 was merged into main in PR #2 and is available under Portfolio → Annual strategy | Annual GARCH parameter refitting below does not change portfolio weights. The Phase 11 results remain a separate experiment from this lab. |
| Alternative allocations | Minimum empirical 95% ES; policy-constrained variance-risk balancing | No future superiority, global risk-parity optimality, alternative-candidate crisis/forecast calibration or client suitability. |
| Robustness | Earlier/trailing training windows, expected-return shocks, fixed covariance shrinkage and block resampling | No optimal shrinkage estimate, exhaustive perturbation search or calibrated weight confidence intervals. |
| Changing volatility/dependence | GARCH Normal/FHS forecasts, EWMA covariance, dated tests and prior-volatility diagnostics | No fitted Markov-switching model, DCC or copula. Regime labels are descriptive. |
| Spending sustainability | Joint return/inflation block simulations over 120 months; withdrawal and inflation-uplift sensitivity | Frequencies are conditional on a short recent sample, not calibrated future survival probabilities. Actual liabilities remain unknown. |
| Separate income | Constant-notional ex-date distribution proxy and ledger | Actual payment-date cash accounting/taxes missing; split-exposed candidates withheld pending unit review. |
| Detailed implementation | Trading/admin cost sensitivity and lagged-volume participation proxy | Actual bid-ask quotes, calibrated market impact, withholding, minimum lots and execution constraints unavailable. |

The design was created after viewing validation/evaluation outcomes. Strict past-only input timing prevents mechanical look-ahead in forecasts and fits; it does **not** make the model-selection exercise an untouched holdout experiment. No result automatically revises the existing recommendation or policy.

## 1. Alternative allocations

Both alternatives use only development simple returns before 2019-01-01, all seven eligible ETFs and the existing construction limits. No constraints are loosened to improve evaluation results.

**Minimum ES:** minimise `eta + mean(max(-R*w - eta, 0))/(1-0.95)` with fully invested, long-only policy-constrained weights. A sparse linear programme uses SciPy HiGHS. Its objective is reconciled against the existing empirical integral-quantile ES, including fractional tail mass. Solver failure is explicit. This follows the [Rockafellar-Uryasev CVaR formulation](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf); the library interface is documented in [SciPy linprog](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linprog.html).

**Constrained risk parity:** minimise squared deviations of `w_i*(Sigma*w)_i/(w' Sigma w)` from `1/7`. These signed variance-risk shares sum to one. Use two deterministic feasible SLSQP starts and retain the lower successful training objective; global optimality is not proved. Policy constraints can prevent exact equality. The measured maximum share gap and equality flag are exported; equality uses absolute share tolerance `1e-4`. This is constrained risk balancing, not a claim that capital weights or achieved risks are equal. See [Maillard, Roncalli and Teiletche](https://www.thierry-roncalli.com/download/erc.pdf).

Numerical near-zero weights are clipped, normalised to funded unit sum and policy-validated. All five candidates are then compared with separate USD 10m starts on validation and evaluation, identical month-end trading and gross-trade costs, and no withdrawals. Wealth includes opening cost; funded-NAV drawdown includes initial capital. These are historical monthly-rebalanced paths, not one-day exposure-loss samples.

## 2. Allocation robustness

Original minimum-volatility and maximum-Sharpe weights are compared with:

- Full development; final five/ten development years; development ending one year earlier.
- SPY arithmetic annual mean shifted by -2/+2 percentage points, holding covariance fixed.
- `0.75*sample_covariance + 0.25*diagonal(sample_covariance)`. The intensity is prespecified and is **not** estimated optimal Ledoit-Wolf shrinkage.
- Thirty geometric-block resamples with expected length 20 sessions, using common sampled return/risk-free rows and seed `20261030`.

All variants exclude 2019 onward. Report half the L1 weight difference (one-way target change), maximum asset change and descriptive bootstrap weight quantiles. Failed fits remain rows with reasons and missing weights; they are not discarded as successes. No evaluation return selects a variant. The resampling idea comes from the [stationary bootstrap literature](https://statistics.stanford.edu/technical-reports/stationary-bootstrap); small replication counts and historical non-stationarity limit inference.

## 3. GARCH, filtered historical simulation and EWMA dependence

Forecast **fixed target exposures** for the three original portfolios on every prepared 2019–2026 target session. The training window excludes the target return. Each first session of a year refits using the preceding 1,000 sessions; parameters/mean are held for that year, while conditional variance updates after each observed return.

`h[t+1] = omega + alpha*epsilon[t]^2 + beta*h[t]`.

Gaussian variance QMLE conditions on the training sample mean, uses percent scaling, sample residual variance as the initial filter value, two deterministic starts, positive omega and `alpha+beta < 0.999`. It is not joint maximum likelihood over a time-varying mean and does not export parameter confidence intervals. Failed annual fits leave that year's GARCH forecasts unavailable; they never substitute a static Normal model.

- GARCH Normal uses the conditional standard deviation and Gaussian VaR/ES.
- GARCH FHS scales empirical tails of the training-standardised residuals by next-session volatility. The residual distribution is frozen until the next annual fit; extremes remain sample-sensitive.
- EWMA jointly updates the seven-asset covariance after observed returns with decay 0.94. At the annual origin its mean and covariance initialise from the past 1,000 sessions. Correlations are dated by the forecast target and retain the preceding as-of date. This is a transparent EWMA design, not DCC or a fitted copula.

See the primary implementation references for [GARCH forecasting](https://bashtage.github.io/arch/univariate/forecasting.html) and [filtered historical VaR](https://bashtage.github.io/arch/univariate/univariate_volatility_forecasting.html). This project implements its documented restricted model with existing SciPy rather than adding the `arch` package.

The lab can compare these forecasts with the existing Historical/Normal references. Changing research dates uses the existing tested `backtest_view` to recalculate coverage, independence and eligible latest-250-session Basel diagnostics. Missing dates are preserved. Sparse transitions and multiple overlapping comparisons limit interpretation; non-rejection is not proof of safety. ES forecasts are displayed, but separate ES severity calibration is not claimed.

Prior-volatility labels use the previous 21 sessions and a pre-2019 median threshold. They provide descriptive counts only. Filtering to disjoint high/low regimes does not justify joining those dates for transition tests.

## 4. Conditional long-horizon spending

Complete calendar-month ETF returns are paired with consecutive monthly CPI changes. The frozen CPI overlap supplies **54 complete rows, February 2022–September 2026**. Missing October 2025 CPI invalidates both its own and November's inflation ratio. Nothing is interpolated. A block must restart at a calendar gap; it cannot bridge the excluded months. Monthly CPI averages remain an approximation to month-end purchasing power.

Sample joint asset-return/inflation rows with geometric expected six-month blocks, 1,000 paths, 120 simulated months and seed `20261030`. Common draws across portfolios/scenarios preserve comparability and contemporaneous dependence. This short recent sample excludes earlier crises and is not an adequate standalone long-run economic model.

Each original frozen portfolio starts with USD 10m, pays opening cost, restores target weights monthly with internally funded gross-trade costs, and pays annual spending after month 12. Initial spending rates are 2%, 3% or 4% of original capital. First payment is that amount; later annual payments follow simulated inflation relative to the first payment's deflator. Additional inflation uplift 0%/2% **multiplies** the annual inflation-growth factor; it is not an additive percentage-point forecast. Sale `S = payment/(1-cost)` funds the cash and sale fee. Insufficient NAV causes explicit shortfall and zero capital, with no borrowing or automatic recovery.

Report no-shortfall frequency, real terminal-wealth quantiles, real-capital preservation, a separate stricter 3%-after-spending growth test, costs and payouts. Every scenario has its own exported fan curves. These are distribution quantiles, not confidence bands for the actual future. Wilson intervals describe conditional Monte Carlo binomial sampling only; zero observed failures is not certainty and neither interval covers model/parameter uncertainty. No actual university spending schedule, taxes or institutional inflation benchmark is assumed known.

## 5. Income and implementation

The verified raw snapshot contains `Dividends`, `Capital Gains`, `Stock Splits`, `Close` and `Volume`. Distribution fields are useful, but their ex-dates are not actual cash payment dates. Provider adjustment errors are possible; see [yfinance's primary repair documentation](https://ranaroussi.github.io/yfinance/advanced/price_repair.html).

The income proxy is `reference capital * target weight * distribution per share / previous Close` for eligible dates **after** allocation. It assumes constant dollar exposure and excludes trading, taxes and cash-account movements. Never add it to adjusted-price portfolio returns, which already reinvest distributions. XLE/XLK split on 5 December 2025 in the snapshot. Candidates holding a split-exposed ETF have their complete income total withheld until the unit convention is independently reviewed. The app separately displays the covered assets, their target-weight share and the sum of their dated proxy ledger; this partial figure is **not** a complete fund-income estimate and cannot be ranked against a complete total. The loader checks that each partial figure reconciles to its ledger. Baseline SPY/AGG has no such split in the measured period and retains a labelled proxy, not actual spendable cash receipts.

Cost scenarios hold targets fixed and vary gross-trade rates 0/10/25 bps and **additional administrative** annual charges 0/25/50 bps. ETF expenses embedded in prices are not charged again. The continuous proportional admin overlay scales NAV by `exp(-fee * calendar_days / 365.25)`; an independent holdings replay verifies the homogeneity identity with returns and rebalancing. No additional liquidation cost is assumed for that administrative deduction.

Policy-cost trades are compared with the preceding 20 observed sessions' mean `Close*Volume`. Today's volume is excluded. Participation is a historical daily-volume proxy requiring split-unit/intraday review; it is not a spread, impact estimate or execution guarantee. No tax rate is fabricated.

## Reproduction, integrity and remaining work

```bash
uv run --locked python commands/run_research.py
```

The existing verified app bundle must exist first; the normal app launcher prepares missing stages. This optional lab writes 18 tables and its summary/manifest under `output/research/<snapshot>/`. Base outputs are not modified. Manifest bindings cover the exact base bundle, input/CPI hashes, Python sources and dependency lock. Loaders reject stale/tampered results, incomplete comparison grids, invalid units/timing or impossible simulation frequencies. Parsed tables are cached with bounded entries; source/output verification still occurs on reruns. Widget changes never refit models or download data.

The core app still opens if optional lab preparation fails, with an explicit unavailable lab reason. Existing report/tear-sheet/committee materials describe the original frozen candidates. Adding these experiments to the final investment argument requires human review and fresh, honestly labelled validation; no worksheet or approval is completed automatically.
