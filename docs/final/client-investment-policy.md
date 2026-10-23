# Serendib University Endowment Fund: investment policy draft

Version 0.1 | 23 October 2026 | Proposed research policy; validation pending

This is a research starting point, not an implemented portfolio, approved client instruction or performance claim. **Brief facts** come from the final challenge, pp. 3-5. All numerical choices beyond the USD 10 million mandate are **team proposals**, to be evaluated before using the final test period. Track evidence in the [requirements checklist](requirements-checklist.md).

## Mandate and objectives

**Brief facts:** manage USD 10 million for a conservative university endowment supporting scholarships, research, faculty development and capital projects. Balance preservation, income and sustainable real growth. Avoiding large losses takes precedence over maximising gains. Eligible investments: SPY, EFA, EEM, AGG, GLD, XLE and XLK. The brief allows any subset, including one fund.

**Proposed horizon:** 10 years, with annual strategic review and monthly monitoring. This reflects the endowment's long-lived mission; a one-day risk estimate is not a ten-year forecast.

**Proposed return objective:** 3% annualised growth of purchasing power over the investment horizon, after modelled trading costs and before withdrawals and taxes. Evaluate real wealth using a disclosed US CPI series from FRED. This is an objective to test, not a promised or estimated return. Client taxes, management fees and spending schedule are unknown and must be disclosed.

**Income and liquidity:** examine holdings' income role separately from total return; adjusted-price gains are not all spendable income. Base comparisons assume reinvested distributions and no external withdrawals. Before claiming support for university spending, add an explicitly hypothetical annual withdrawal of 3% of initial capital, subsequently inflation-adjusted; define its payment date and funding trades. This is a sensitivity scenario, not a known client commitment.

## Proposed construction rules

Weights are portfolio-value fractions at rebalancing. These starting constraints are not organiser-supplied limits.

| Rule | Proposed value | Reason and limitation |
|---|---|---|
| Funding | Long-only; weights total 100%; no leverage or derivatives | Transparent use of eligible ETFs. No additional investable cash/risk-free asset. |
| Bonds | AGG at least 40% | Starting defensive allocation; interest-rate and credit risk remain. |
| Single ETF | At most 60% | Limits fund concentration; deliberately narrower than the brief's single-fund permission. |
| Total equities | SPY + EFA + EEM + XLE + XLK at most 50% | Limits equity exposure; fund count is not diversification. |
| Sector tilts | XLE/XLK each at most 10%; combined at most 15% | Limits additional concentration; overlap with SPY must be assessed. |
| Gold | GLD at most 20% | Allows diversification without excessive reliance on a non-income-producing holding. |

The bounds admit the proposed **40% SPY / 60% AGG comparator**. Arithmetic feasibility does not establish suitable returns or risk. Compare constrained mean-variance candidates with this fixed comparator, using identical accounting and periods. Initially use SPY as the CAPM market proxy and explain its limitations for a mixed-asset portfolio. Test input and constraint sensitivity on development data. An ES-focused candidate is optional after the required baseline works.

## Proposed risk review levels

| Measure | Initial review level | Interpretation |
|---|---|---|
| One-day 99% ES | 2% of current NAV; USD 200,000 at initial capital | Larger estimates require explicit review and an allocation/mandate response. |
| Historical crisis-path maximum drawdown | 15%; USD 1.5m if the relevant peak NAV is USD 10m | Assess peak-to-trough resilience, distinct from end-of-period loss. |
| Hypothetical adverse-scenario loss | 10%; USD 1m at initial capital | Assess documented joint shocks, not an asserted probability. |

These rounded levels make a cautious loss budget discussable; they have not been elicited from the client or calibrated. They are review triggers, not guarantees, stop-loss orders or automatic optimisation constraints. Evaluate their suitability on development data, document revisions and freeze the policy before final evaluation. Do not increase limits after seeing held-out failures merely to manufacture compliance.

Report Historical, Parametric and Monte Carlo VaR and ES at 95% and 99%, with matching horizons/units/signs; support the required 90/95/99% interface and EVT comparison. Choose windows and EVT thresholds without future information, disclose uncertainty and label unsupported estimates. Validate through out-of-sample tests and crisis paths before making a recommendation.

## Implementation and decision rule

**Proposed execution:** monthly rebalancing with signals based only on information available before the execution return; weights drift between rebalances. Assume 10 basis points per dollar traded on gross traded notional and compare 0/25-basis-point scenarios. These are assumptions, not broker quotes. Specify initial trading costs and do not double-count fund expenses embedded in prices. State execution/liquidity limitations.

**Decision:** recommend only an allocation satisfying construction rules with defensible validation and a suitable return/risk trade-off. Explain any review-level breach and alternatives. If objectives and risk tolerances cannot be reconciled, propose adjusted limits/objectives or reject the mandate as posed; report infeasibility openly. No final weights, model or recommendation have yet been selected.

**Governance:** the team must validate AI-assisted work and substantiate its recommendation. Record actual reviewers, data snapshot, configuration, policy version and limitations. Review following a risk-trigger breach, material data/model problem or changed client needs. The final committee retains the decision.

## Team explanation

We are investigating how to grow a university fund while limiting large losses. Our proposed limits give the research a clear starting point. Data and out-of-sample checks must establish whether they are sensible. Neither a return target nor a modelled risk number is a guarantee.
