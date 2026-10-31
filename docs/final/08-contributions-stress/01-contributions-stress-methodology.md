# Portfolio risk contributions and stress methodology

Implemented 25 October 2026. **31 October update:** Mahinsa Kuruppu reported completing the remaining checks and the five-member team accepted the illustrative research scenario in the [manual worksheet](03-manual-stress-check.md). Client policy and allocation approval remain open.

## Scope and comparable inputs

`commands/run_stress.py` uses the frozen snapshot offline. It fits the same development-only baseline, minimum-volatility and maximum-Sharpe allocations as the other runners. Default risk attribution uses 1,000 consecutive exchange-session simple returns through the as-of close, 95%/99% confidence and USD 10m per allocation. The forecast horizon is the next exchange session. No future observations enter the attribution window. Candidate weights use data through 31 December 2018; an earlier as-of date is rejected.

This phase implements Normal marginal/component VaR and ES, empirical Historical ES contributions, funded sizing checks, three historical replays and an illustrative joint shock. It does not claim marginal Historical VaR, Monte Carlo or EVT allocation formulas. Empirical VaR is nonsmooth; assigning standalone ETF VaR/ES to the portfolio would not provide the requested portfolio attribution.

## Marginal versus component risk

For daily asset means `mu`, sample covariance `Sigma`, weights `w`, portfolio mean `m=w' mu` and volatility `s=sqrt(w' Sigma w)`:

```text
Normal VaR = -m + z(c) s
Normal ES  = -m + phi(z(c))/(1-c) s
Marginal_i = -mu_i + k (Sigma w)_i / s
Component_i = w_i × Marginal_i
```

Here `k` is `z(c)` for VaR and `phi(z(c))/(1-c)` for ES. Components sum to total portfolio risk, including its mean term. Multiplying fractions by NAV converts to USD; multiplying by 100 gives percentages. A marginal is the derivative with respect to unrestricted exposure weight, not an amount of risk already held. Its one-percentage-point USD effect is `0.01 × NAV × Marginal_i` before specifying funding.

Zero-held assets have zero components but can have nonzero marginals. Negative components are retained as hedge offsets; other component shares can exceed 100%. Shares are unavailable when total risk is approximately zero. Deterministic assets use the negative-mean gradient. A zero/near-zero volatility hedge of risky assets has an undefined/unstable gradient, explicitly reported as unavailable.

For Historical ES, form each observation's portfolio loss `L=-R w`. The tail contains exactly `n(1-c)` observations' probability mass, including fractional boundary mass. Above-VaR losses receive full mass; remaining mass is shared equally among observations tied at VaR. The normalized tail-weighted asset losses are marginals/subgradients; multiplying by holdings gives additive ES components. Boundary ties can make the derivative nonunique, so the chosen symmetric subgradient is labeled. Fewer than 20 effective tail observations is flagged. With 1,000 observations at 99%, only ten observations' mass determines ES.

## Allocation sizing

Every directed 1 percentage point donor-to-receiver transfer among seven ETFs is examined. Insufficient donor holdings or a policy violation is recorded as infeasible. Feasible changes are repriced on the same window for Normal VaR, Normal ES and Historical ES:

```text
Approximate change = 0.01 × (Marginal_receiver - Marginal_donor)
Exact change = Risk(changed weights) - Risk(original weights)
```

Use exact repricing for interpretation. A finite transfer can change portfolio volatility or tail membership; a selected tie subgradient need not predict every direction. The table is a sensitivity check, not a new optimiser or investment recommendation. It excludes trading costs and does not establish a return benefit. Choosing a transfer after viewing evaluation results would require a separate, honestly labeled decision/validation process.

## Historical stress accounting

Requested periods are calendar 2008, March 2020 and calendar 2022 (end dates exclusive: 2009-01-01, 2020-04-01 and 2023-01-01). Each must contain the entire expected XNYS session calendar. Missing, extra or invalid observations make that replay unavailable; no shortened or filled crisis is substituted. These named windows do not represent the full peak-to-trough duration of every crisis.

Each replay starts at USD 10m on the close immediately preceding its first return. Buy-and-hold asset values compound separately, with portfolio weights drifting. No rebalancing, fees, withdrawals or additional dividend cash flows are added to adjusted-price returns. Initial capital is included in the drawdown path. Terminal loss, worst daily loss, worst loss from initial capital and maximum peak-to-trough drawdown are distinct quantities. Drawdown USD uses the actual peak NAV associated with maximum percentage drawdown, not necessarily USD 10m. Asset terminal-loss components reconcile to terminal portfolio loss; they are not drawdown contributions.

These are retrospective exposure replays using historical ETF returns, not investment track records. The baseline 40/60 target is preset; only the minimum-volatility and maximum-Sharpe allocations were fitted through 2018 and therefore unavailable in 2008. The current `weights_available_at_start` field compares the shared 2018 fitting cutoff with the replay start for every portfolio; its `False` value for the preset baseline must not be read as evidence that 40/60 was estimated from 2018 data. The 2022 replay also describes a different convention from the monthly-rebalanced performance backtest after costs.

## Hypothetical scenario and review levels

The one-session inflation/liquidity squeeze assumes rising real yields/credit spreads, equity weakness, forced selling in bonds/gold and an energy-demand shock. Direct ETF total-return shocks are SPY -12%, EFA -15%, EEM -18%, AGG -6%, GLD -4%, XLE -20%, XLK -18%. This AI-assisted draft was reported accepted by the five-member team on 31 October as an illustrative research scenario, not a calibrated macro-factor model or client-approved policy. Development-period worst daily ETF returns are supplied as scale context, not jointly observed shocks or a calibration claim.

Portfolio loss is `-sum(weight × shock)`; signed asset losses sum exactly to it. Half/base/1.5-times shocks test severity sensitivity, not likelihood or confidence. Scaled returns below -100% are rejected.

Proposed research review levels are 2% one-day 99% ES, 15% historical maximum drawdown and 10% hypothetical loss. These have different horizons and denominators and must not be treated as interchangeable limits. A value strictly above its matching level triggers review. Passing a level does not establish client suitability, and these numbers are not client-approved limits.

## Files, evidence and limitations

- `src/saifa/domain/config.py`: scenarios, levels and validated settings; `src/saifa/domain/stress.py`: typed results.
- `src/saifa/models/contributions.py`: attribution and funded transfers; `src/saifa/models/stress.py`: replay and shock accounting.
- `src/saifa/application/stress_pipeline.py`: shared inputs, provenance and additive checks.
- `src/saifa/reporting/stress.py`: report and five charts; `tests/test_stress.py`: independent arithmetic, derivatives, boundaries, calendars and future-data exclusion.

The run folder records input returns, moments, weights, scenario inputs, results, source/dependency/input hashes, package versions and a status file. Only `complete` runs may be used, and row-level availability/warnings must still be checked. Settings identify folders; changing code can overwrite the same settings folder, with the updated code hashes retained in its metadata. Generated outputs remain outside Git and must be regenerated or packaged separately for submission.

Normal attribution inherits Normal-tail assumptions. Historical ES is sample-sensitive. Stress scenarios are selected possibilities, not forecasts or exhaustive worst cases. Liquidity, market impact, spending needs, intra-day paths and forced rebalancing are unmodelled. Existing coverage/clustering test failures remain relevant; this phase does not validate ES forecast severity or approve a model.

References: [Tasche, Euler capital allocation](https://arxiv.org/abs/0708.2542) motivates additive marginal/component allocation. [BCBS stress testing principles](https://www.bis.org/publications/201810-guidelines-stress-testing-principles) motivates explicit scenario assumptions and interpretation; no regulatory-compliance claim is made.
