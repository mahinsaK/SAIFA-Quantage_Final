# Final challenge requirements checklist

Version 0.1 | 23 October 2026 | Planning baseline

This tracks the final challenge, not the screening submission. Unchecked means not yet demonstrated for the final challenge. Reusable screening code does not automatically satisfy a requirement.

## Sources and interpretation

- Source: *Quant edge 1.0 Final Challenge*, October 2026, 10 pages. Local source: `/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Final_Challenge/Quant edge 1.0 Final Challenge 1.pdf`.
- Deadline: **31 October 2026**, supplied by the team. Exact time, timezone, submission route and pitch date remain unconfirmed. Internal completion target: **30 October**.
- **Brief requirement** means explicitly requested. **Team plan** means our proposed implementation or verification. Numerical policy assumptions are not organiser-supplied limits.
- The brief permits one eligible fund or any combination. Copulas, wavelets, GARCH, paid hosting and deep learning are not mandatory.
- The named crisis episodes are examples; our plan covers all three subject to verified data coverage.
- KPI examples are not an exhaustive specification. We plan to implement every named KPI. Interpret the brief's "Calmer Ratio" as the standard Calmar ratio and document its definition.
- Do not carry screening ZIP-size, Drive-link or deadline-time rules into the final round without confirmation.

## Definition of done

Record a repository file/output and actual reviewer when marking an item complete. Numerical evidence must identify data snapshot, configuration and code revision. A chart alone does not prove correctness. The baseline accounting reviewer is recorded; reviewers for the remaining open items still need to be assigned.

**23 October data update:** data acquisition, frozen snapshots, calendar/quality checks, asset returns, lagged FRED rates and descriptive ADF are implemented. [Data milestone evidence](data-milestone.md) records the live dataset, 21 data-focused tests and offline reproduction. D01-D03 and D05-D07 now have automated implementation evidence; their final team sign-off remains open. D04 initially had asset-return evidence and is completed by the baseline update below. V05 remains open because the completed accounting review covers only one part of the wider human-validation requirement.

**Baseline update:** 40% SPY / 60% AGG buy-and-hold and monthly-rebalanced comparators, exact 10 bps gross-trade costs, daily weights/NAV, cumulative and annualised returns, volatility and drawdown are implemented. The accounting was manually validated by Mahinsa Kuruppu on 23 October 2026: Parts A-C matched and the focused test suite passed. See [methodology](baseline-methodology.md) and the completed [manual check](manual-accounting-check.md). M06 has baseline evidence but remains open until the final investment interpretation is complete. D04 now has portfolio accounting and named human-review evidence.

**Optimisation update:** constrained minimum-volatility and maximum-Sharpe candidates, a 25-point efficient frontier, CAPM and all named performance ratios are implemented with a chronological development/validation/evaluation split. See [methodology](optimisation-methodology.md), [milestone evidence](optimisation-milestone.md) and the pending [manual check](manual-optimisation-check.md). M04 and M05 have automated evidence but remain open until team review and final interpretation.

### Mandate and portfolio construction

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | M01 | USD 10m conservative endowment: preservation, income, real growth (pp. 3-4) | Recommendation addresses all objectives; risk in percent and USD. |
| [ ] | M02 | Defend horizon and return objective (p. 4) | Evaluate [policy draft](client-investment-policy.md); distinguish objectives from forecasts and document inflation, costs and withdrawals. |
| [ ] | M03 | Justified constraints and eligible universe (pp. 4-5) | Feasibility and weight checks; permitted tickers exactly SPY, EFA, EEM, AGG, GLD, XLE, XLK. |
| [ ] | M04 | Markowitz mean-variance and CAPM (p. 7) | Portfolio/frontier comparison, optimizer status, inputs; market proxy, risk-free conversion, beta/alpha and limitations. |
| [ ] | M05 | Performance KPIs (p. 7) | Team plan: Sharpe, Sortino, Treynor, Jensen alpha, Information ratio, maximum drawdown and Calmar; definitions, annualisation and undefined cases. |
| [ ] | M06 | Diversification, suitability and return/risk trade-offs (pp. 4, 8) | Compare with fixed benchmark on consistent periods, costs and accounting; explain the client's benefit and sacrificed return. |

### Data governance

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | D01 | Approved sources (p. 9) | Yahoo Finance via yfinance for ETFs; FRED for risk-free/macro; World Bank/IMF if relevant. Manifest records sources, dates, settings, coverage and snapshot. |
| [ ] | D02 | Adjusted close (p. 9) | Verify downloaded field is adjusted; explain dividends/splits and avoid double-counting distributions. |
| [ ] | D03 | Calendar alignment and non-overlap policy (p. 9) | Coverage/missingness table; reproducible holiday policy; no backward fill or silent fabrication. |
| [x] | D04 | Log returns for statistics; justify simple returns (p. 9) | Both defined; correct simple-return portfolio accounting, compounding, rebalancing and costs. |
| [ ] | D05 | Flag suspicious data, document outliers (p. 9) | Stale/flat prices, breaks, jumps and negative-price flags with disposition log; genuine crisis returns retained. |
| [ ] | D06 | Basic stationarity check (p. 9) | ADF specification, sample, results and interpretation on modelled returns; no claim that a test proves stationarity. |
| [ ] | D07 | Reproducible cleaning, no manual hidden edits (p. 9) | Raw-to-clean pipeline regenerates data and audit outputs from snapshot. |

### Risk models and validation

**VaR/ES implementation update:** R01-R03 now have automated evidence from Historical, Parametric Normal and correlated Gaussian Monte Carlo estimates at 95%/99%. The methods use identical one-session target exposures, USD 10m NAV, 1,000-observation window and signed-loss convention. See [methodology](risk-methodology.md), [milestone](risk-milestone.md) and [manual worksheet](manual-risk-check.md). These requirements remain unchecked until named human review and final interpretation. The output is an as-of risk comparison; V01-V04 remain outstanding. The estimator also supports 90% for the future interface, but U02 is not implemented.

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | R01 | Historical, Parametric, Monte Carlo VaR at 95% and 99% (p. 7) | Same portfolio, horizon, window and sign convention; repeatable simulation seed. |
| [ ] | R02 | Explain method disagreements and assumptions (p. 7) | Discuss tails, distributional assumptions and sampling error; report agreement honestly when assumptions imply it. |
| [ ] | R03 | ES and rationale (p. 7) | Matching confidence/horizon; explanation of losses beyond VaR and why neither is a guaranteed loss ceiling. |
| [ ] | R04 | EVT and justified threshold (p. 7) | Diagnostics, exceedance count, parameters, uncertainty and sensitivity; threshold selected without final-test information. |
| [ ] | R05 | Model limitations and stressed behaviour (p. 7) | Stress-period comparison; unreliable/undefined estimates visibly flagged rather than fabricated. |
| [ ] | V01 | Out-of-sample selected VaR models (p. 7) | Timestamped forecasts/losses; training, validation and final-test boundaries. Team plan: walk-forward evaluation without future-data leakage. |
| [ ] | V02 | Kupiec proportion-of-failures test (p. 7) | Exceptions, observations, expected rate, statistic, p-value, interpretation and edge cases. |
| [ ] | V03 | Christoffersen independence test (p. 7) | Transition counts, statistic/p-value; insufficient transitions explicitly flagged, not treated as a pass. |
| [ ] | V04 | Basel traffic light (p. 7) | Canonical 250-observation/99% view. Other settings use a labelled, justified adaptation; no regulatory-compliance claim. |
| [ ] | V05 | Human validation (pp. 8-9); team test plan | Hand-worked checks, analytical/simulation checks, accounting and future-data leakage checks; actual reviewer records. |

### Investor decisions and stress

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | S01 | Marginal VaR/ES contributions and sizing (p. 8) | Define marginal versus weighted/component contributions; show allocation implications. Standalone asset ES is not portfolio ES contribution. |
| [ ] | S02 | Historical crisis return paths (p. 8) | Team plan: 2008, March 2020 and 2022. Exact dates, coverage, paths, cumulative loss and drawdown; distinguish replay from a genuine historical strategy backtest. |
| [ ] | S03 | One team-designed hypothetical scenario (p. 8) | Economic narrative, joint ETF shocks, percent/USD impact; severity is not an asserted probability. |
| [ ] | S04 | One-page plain-English committee recommendation (p. 8) | Accept as proposed / adjust risk limits / reject; allocation, evidence, trade-offs, uncertainty and review triggers. |

### Interface, deliverables and accountability

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | U01 | Python, Streamlit, free-tier resources (pp. 5-6) | Runnable application and dependency list without paid data/compute dependency. |
| [ ] | U02 | Sidebar controls (p. 5) | Confidence 90/95/99%, VaR method and backtest date range actually update results; invalid choices explained. |
| [ ] | U03 | Portfolio panel (p. 5) | Weights, cumulative return and drawdown with period and rebalance convention. |
| [ ] | U04 | Side-by-side VaR, ES, EVT (p. 5) | Matching selected confidence, horizon and units. Unsupported EVT threshold/confidence combinations explained; resolve usable coverage before sign-off. |
| [ ] | U05 | Backtesting panel (p. 5) | Kupiec/Christoffersen results and traffic light with sample/model context. |
| [ ] | U06 | Stress panel (p. 6) | Portfolio impact for each crisis/scenario, with dates and assumptions. |
| [ ] | U07 | Assumptions & Limitations page (p. 6) | Plain language; data, model, uncertainty, liquidity, costs and missing client information; consistent with report. |
| [ ] | O01 | Judge-accessible GitHub and README (p. 6) | Access checked; installation, app launch, frozen-data reproduction and refresh instructions. |
| [ ] | O02 | Deployed OR locally one-command runnable app (p. 6) | Clean-environment launch; hosting optional, local fallback if hosted. |
| [ ] | O03 | 7-15-page report/investment memo (p. 6) | Methodology, data/cleaning, results, assumptions and limitations; values match frozen app outputs. |
| [ ] | O04 | One-page executive tear sheet (p. 6) | Allocation, risks and decision readable in under five minutes. Team plan: supply separately from S04 to cover both requests explicitly. |
| [ ] | O05 | AI disclosure and team understanding (pp. 8-9) | Tools, purposes, material generated components and actual human validation; team can explain decisions, assumptions and code. |
| [ ] | O06 | Teams of five; final-five pitch (pp. 2, 6) | Roster confirmed. If selected for final five: 10-12-minute deck/pitch plus Q&A. Pitch date unconfirmed. |

## Decisions still to validate

| Item | Working proposal | Required resolution |
|---|---|---|
| Horizon / objective | 10 years; 3% annualised real growth after modelled trading costs, before withdrawals | Suitability and feasibility assessed on development data |
| Constraints / risk triggers | Defined in companion policy | Feasibility and sensitivity, then policy freeze |
| Spending / liquidity | No client schedule given | Explicitly hypothetical withdrawal analysis, not invented client commitments |
| Sample / windows | Unset | Verify ETF/crisis coverage and enough tail observations; freeze before evaluation |
| Benchmarks | 40% SPY / 60% AGG comparator; SPY CAPM proxy | Explain suitability and mixed-asset proxy limitations |
| Logistics | 31 Oct deadline | Exact time/timezone, submission route and pitch date |
| Owners / reviewers | Unassigned | Record actual members and review outcomes |

## Sequence and ownership

Suggested five roles: mandate/portfolio, data/reproducibility, risk/EVT, validation/stress, app/report. Assign a different reviewer to material calculations. Every member should explain the objective, VaR versus ES, allocation and limitations.

| Target date | Deliverable |
|---|---|
| 23 Oct | Checklist and policy draft; team concept walkthrough; preserve screening revision before implementation |
| 24 Oct | Audited data, simple benchmark and accounting checks; app skeleton and report outline |
| 25 Oct | Portfolio construction, CAPM, KPIs; freeze policy/model selection before final evaluation |
| 26 Oct | Three VaR methods, ES and small-number verification |
| 27 Oct | EVT diagnostics, sensitivity and threshold explanation |
| 28 Oct | Out-of-sample tests, contributions and stress analysis |
| 29 Oct | Integrated app and team-developed investment decision |
| 30 Oct | Report, tear sheet, committee memo, disclosure and clean-environment rehearsal |
| 31 Oct | Final access/consistency checks and submission before confirmed cutoff |

Rubric: decision-making 30%, technical correctness 25%, software 15%, innovation 15%, communication/defence 15% (p. 10). Optional extensions must not delay required work. Candidate extension: compare tail/stress-aware allocation with the baseline and show the return sacrificed for lower losses; no advantage is assumed.

## Planning completion

- [x] Brief reviewed and requirements mapped to pages and acceptance evidence.
- [x] Policy draft written with explicit assumption labels.
- [x] Confirmed deadline date separated from unconfirmed time and pitch date.
- [ ] Team assigns owners and explains policy in its own words.
- [ ] Numerical assumptions evaluated on development data and policy frozen.
- [ ] Final requirements above verified with evidence and actual review.
