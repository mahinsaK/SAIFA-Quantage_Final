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

**23 October data update:** data acquisition, frozen snapshots, calendar/quality checks, asset returns, lagged FRED rates and descriptive ADF are implemented. [Data milestone evidence](../02-data/02-data-milestone.md) records the live dataset, 21 data-focused tests and offline reproduction. D01-D03 and D05-D07 now have automated implementation evidence; their final team sign-off remains open. D04 initially had asset-return evidence and is completed by the baseline update below. V05 remains open because the completed accounting review covers only one part of the wider human-validation requirement.

**Baseline update:** 40% SPY / 60% AGG buy-and-hold and monthly-rebalanced comparators, exact 10 bps gross-trade costs, daily weights/NAV, cumulative and annualised returns, volatility and drawdown are implemented. The accounting was manually validated by Mahinsa Kuruppu on 23 October 2026: Parts A-C matched and the focused test suite passed. See [methodology](../03-baseline/01-baseline-methodology.md) and the completed [manual check](../03-baseline/03-manual-accounting-check.md). M06 has baseline evidence but remains open until the final investment interpretation is complete. D04 now has portfolio accounting and named human-review evidence.

**Optimisation update:** constrained minimum-volatility and maximum-Sharpe candidates, a 25-point efficient frontier, CAPM and all named performance ratios are implemented with a chronological development/validation/evaluation split. See [methodology](../04-optimisation/01-optimisation-methodology.md), [milestone evidence](../04-optimisation/02-optimisation-milestone.md) and the pending [manual check](../04-optimisation/03-manual-optimisation-check.md). M04 and M05 have automated evidence but remain open until team review and final interpretation.

### Mandate and portfolio construction

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | M01 | USD 10m conservative endowment: preservation, income, real growth (pp. 3-4) | Recommendation addresses all objectives; risk in percent and USD. |
| [ ] | M02 | Defend horizon and return objective (p. 4) | Evaluate [policy draft](02-client-investment-policy.md); distinguish objectives from forecasts and document inflation, costs and withdrawals. |
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

**EVT implementation and manual review (24 Oct):** R04 has POT/GPD VaR/ES, a prespecified 90% threshold rationale, development/as-of diagnostics, six-threshold sensitivity, Q-Q and parameter plots, and circular block-bootstrap uncertainty. Undefined ES, insufficient tails and unsupported confidence levels are explicitly unavailable. Mahinsa Kuruppu completed the arithmetic and signed off the 90% threshold as a provisional research choice; see [methodology](../06-evt/01-evt-methodology.md), [milestone](../06-evt/02-evt-milestone.md) and [manual check](../06-evt/03-manual-evt-check.md). Parameter stability is imperfect and no optimal-threshold or coverage claim is made. V01-V04 and stress validation remain open.

**VaR/ES implementation update:** R01-R03 now have automated evidence from Historical, Parametric Normal and correlated Gaussian Monte Carlo estimates at 95%/99%. The methods use identical one-session target exposures, USD 10m NAV, 1,000-observation window and signed-loss convention. See [methodology](../05-risk-models/01-risk-methodology.md), [milestone](../05-risk-models/02-risk-milestone.md) and [manual worksheet](../05-risk-models/03-manual-risk-check.md). These requirements remain unchecked until named human review and final interpretation. The output is an as-of risk comparison; V01-V04 remain outstanding. The estimator also supports 90% for the future interface, but U02 is not implemented.

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | R01 | Historical, Parametric, Monte Carlo VaR at 95% and 99% (p. 7) | Same portfolio, horizon, window and sign convention; repeatable simulation seed. |
| [ ] | R02 | Explain method disagreements and assumptions (p. 7) | Discuss tails, distributional assumptions and sampling error; report agreement honestly when assumptions imply it. |
| [ ] | R03 | ES and rationale (p. 7) | Matching confidence/horizon; explanation of losses beyond VaR and why neither is a guaranteed loss ceiling. |
| [x] | R04 | EVT and justified threshold (p. 7) | Diagnostics, exceedance count, parameters, uncertainty and sensitivity; 90% provisional rule reviewed and signed, with limitations. Forecast validation tracked separately in V01-V04. |
| [ ] | R05 | Model limitations and stressed behaviour (p. 7) | Stress-period comparison; unreliable/undefined estimates visibly flagged rather than fabricated. |
| [ ] | V01 | Out-of-sample selected VaR models (p. 7) | Implemented timestamped past-only forecasts for all four candidates, fixed development weights and separate validation/evaluation periods; retrospective-evaluation caveat. Named human interpretation pending. |
| [ ] | V02 | Kupiec proportion-of-failures test (p. 7) | Implemented counts, expected rate, LR/p-value, exact binomial diagnostic and boundary/missing cases. Hand likelihood and automated checks supplied; human review pending. |
| [ ] | V03 | Christoffersen independence test (p. 7) | Implemented transition counts and LR/p-value; missing/insufficient evidence unavailable, sparse cells warned. Manual transition exercise supplied; human review pending. |
| [ ] | V04 | Basel traffic light (p. 7) | Implemented canonical rolling/latest 250-session/99% views, reset by period; other confidence levels have no colour. No regulatory-compliance claim. Human interpretation pending. |
| [ ] | V05 | Human validation (pp. 8-9); team test plan | Hand-worked checks, analytical/simulation checks, accounting and future-data leakage checks; actual reviewer records. |

**Backtesting implementation update (24 Oct):** V01–V04 now have code and automated evidence: 1,963 next-session targets, 47,112 forecasts, 48 separate-period test summaries and dated rolling Basel results. See [methodology](../07-backtesting/01-backtesting-methodology.md), [milestone evidence](../07-backtesting/02-backtesting-milestone.md) and the pending [manual worksheet](../07-backtesting/03-manual-backtest-check.md). Earlier references to pending forecast validation describe the previous milestone. Some coverage and independence nulls are rejected; implementation completion does not mean all models are approved. The requirements stay unchecked until named human review and final interpretation. ES severity backtesting is not claimed.

### Investor decisions and stress

**Contributions and stress update (25 Oct):** S01–S03 now have implementation and automated evidence: additive Normal VaR/ES and Historical ES contributions, policy-constrained funded transfer sensitivity, full-calendar 2008/March 2020/2022 buy-and-hold replays and a proposed joint shock with severity sensitivity. See [methodology](../08-contributions-stress/01-contributions-stress-methodology.md), [milestone evidence](../08-contributions-stress/02-contributions-stress-milestone.md) and the pending [manual worksheet](../08-contributions-stress/03-manual-stress-check.md). The hypothetical scenario still needs team approval. All three allocations breach the proposed drawdown review level in 2008 and 2022; R05 and the final suitability decision must retain this evidence and earlier forecasting limitations. S01–S03 remain unchecked until named human review and interpretation; S04 and the interface remain outstanding.

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | S01 | Marginal VaR/ES contributions and sizing (p. 8) | Define marginal versus weighted/component contributions; show allocation implications. Standalone asset ES is not portfolio ES contribution. |
| [ ] | S02 | Historical crisis return paths (p. 8) | Team plan: 2008, March 2020 and 2022. Exact dates, coverage, paths, cumulative loss and drawdown; distinguish replay from a genuine historical strategy backtest. |
| [ ] | S03 | One team-designed hypothetical scenario (p. 8) | Economic narrative, joint ETF shocks, percent/USD impact; severity is not an asserted probability. |
| [ ] | S04 | One-page plain-English committee recommendation (p. 8) | Accept as proposed / adjust risk limits / reject; allocation, evidence, trade-offs, uncertainty and review triggers. |

### Interface, deliverables and accountability

**Streamlit implementation update (25 Oct):** U01–U07 now have automated implementation evidence: all five pages, real 90/95/99% selection, dated-forecast test recalculation, unavailable EVT/short-window states, explicit financial conventions, stress breaches and limitations. The offline preparation command produces a hash-verified bundle; the local app launched and its health endpoint responded. See [methodology](../09-streamlit-app/01-app-methodology.md), [milestone](../09-streamlit-app/02-app-milestone.md) and the pending [manual browser check](../09-streamlit-app/03-manual-app-check.md). Browser visual inspection was unavailable in the agent session; final human UI acceptance remains open, so these rows are not marked signed off. Hosting, judge-access checks and final investment approval are separate.

| Done | ID | Brief requirement and source | Acceptance evidence |
|---|---|---|---|
| [ ] | U01 | Python, Streamlit, free-tier resources (pp. 5-6) | Runnable application and dependency list without paid data/compute dependency. |
| [ ] | U02 | Sidebar controls (p. 5) | Confidence 90/95/99%, VaR method and backtest date range actually update results; invalid choices explained. |
| [ ] | U03 | Portfolio panel (p. 5) | Weights, cumulative return and drawdown with period and rebalance convention. |
| [ ] | U04 | Side-by-side VaR, ES, EVT (p. 5) | Matching selected confidence, horizon and units. 90/95/99% available on the frozen snapshot; 90% EVT is explicitly the empirical-threshold VaR with GPD ES. Genuine unavailable cases retained. Reviewer reported completing the new boundary calculation and UI checks on 27 October; see the Phase 06 boundary update. Final team acceptance of the app remains open. |
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
| Sample / windows | Development through 2018; validation 2019–2021; evaluation 2022–22 Oct 2026; rolling risk window 1,000 sessions | Existing evaluation has been viewed; retain retrospective caveat and avoid post-hoc selection. Stress coverage and final team interpretation remain open. |
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

## Phase 10 implementation update - 26 October 2026

S04/O03/O04 now have AI-assisted draft artifacts generated from the same verified bundle as the app: a conditional committee recommendation, 7-15-page report and separate one-page executive tear sheet. See [methodology](../10-investment-decision/01-decision-methodology.md), [milestone](../10-investment-decision/02-decision-milestone.md) and [manual review](../10-investment-decision/03-manual-decision-check.md). These rows remain unchecked until actual team interpretation, document acceptance and final access checks.

M01/M02/M06 now have an explicit decision response, observed real-growth comparison and spending sensitivity. The current recommendation defers implementation, retaining minimum volatility as a conditional discussion candidate; all portfolios breach proposed crisis review levels. The original 3% real target is before spending; a separate FRED CPIAUCSL overlay shows 0.68% / 2.54% / 2.71% annual real growth from 2022-01-03 to 2026-09-30, all below 3% in that shorter period. The after-spending 3% test remains a separately labelled stricter hypothetical scenario. Observed inflation does not establish ten-year sustainability or actual client spending suitability. See the [new CPI review](../10-investment-decision/04-observed-cpi-review.md).

Implementation evidence does not complete V05, O05 or the new CPI human worksheet. Scenario approval, client policy approval, team acceptance of the recommendation, spending/liquidity needs, independent CPI review, browser acceptance, repository access, final cutoff and submission delivery remain human actions. Earlier dated milestone notes describe their own phase, not the current cumulative implementation status.

**Judge launch follow-up:** `uv run --locked python commands/run_judge_app.py` now verifies and reuses existing outputs or builds the missing app/decision/PDF artifacts from the frozen snapshot, then starts Streamlit. An isolated ZIP-style copy without `.git` or generated outputs successfully built every stage and launched the app with a passing health check; matching PDFs were byte-identical. Human browser sign-off and judge-access checks remain open, so O02 stays unchecked pending those checks.

**Pip-only launch follow-up (28 Oct):** `python run_with_pip.py` creates a local virtual environment, installs versions exported from the committed lockfile using pip, and calls the same offline judge launcher. A real Python 3.11 pip installation completed, `pip check` found no broken requirements, the local app health endpoint returned `ok`, and a second launch skipped installation. See the README for platform-specific Python commands. Judge access and a clean source-only pip launch still need checking; O02 remains open.
