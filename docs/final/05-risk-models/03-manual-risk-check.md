# Manual one-day VaR and Expected Shortfall check

Status: **manual calculations and output checks signed off; interpretation draft recorded for reviewer confirmation**. Model calibration and final portfolio suitability remain under review.

Calculate independently with paper/calculator or a separate spreadsheet, then compare with the answers below. These artificial examples verify arithmetic; they are not estimates of the actual fund. No one needs to calculate 200,000 Monte Carlo scenarios by hand.

## Part A: holdings, loss sign and USD

A USD 10 million portfolio holds 40% SPY and 60% AGG. Over one session SPY returns -2% and AGG returns +0.5%. There is no trade or extra fee during this example.

```text
Portfolio return = 0.4*(-0.02) + 0.6*(0.005) = -0.005 = -0.5%
Loss fraction = -portfolio return = +0.005
Dollar loss = 10,000,000 * 0.005 = USD 50,000
Ending wealth = USD 9,950,000
```

If the portfolio rises by 0.5%, the signed loss is -USD 50,000. Do not discard the minus sign.

## Part B: historical VaR and ES

Imagine 100 equally likely one-day losses in ascending order:

`0.0%, 0.1%, 0.2%, ..., 9.8%, 9.9%`.

Use the smallest loss whose cumulative probability reaches the confidence level.

| Calculation | Expected result |
|---|---|
| 95% VaR | 95th observation = 9.4% = USD 940,000 |
| Worst 5 losses | 9.5%, 9.6%, 9.7%, 9.8%, 9.9% |
| 95% ES | Their mean = 9.7% = USD 970,000 |
| 99% VaR | 99th observation = 9.8% = USD 980,000 |
| 99% ES | Worst one observation = 9.9% = USD 990,000 |

ES is at least VaR. Do not include the 95th observation in the worst-five average; that would average six observations.

Optional fractional-tail exercise: at 95.5% confidence the worst tail contains 4.5 observations. VaR is 9.5%; ES is `(9.6 + 9.7 + 9.8 + 9.9 + 0.5*9.5)/4.5 = 9.722222%`.

## Part C: Parametric Normal

Assume daily expected portfolio return `m = 0.001` (0.1%) and daily volatility `s = 0.02` (2%). At 95% confidence use `z = 1.644853627` and Normal density `phi(z) = 0.1031356404`.

```text
VaR = -0.001 + 0.02*1.644853627
    = 0.03189707254 = 3.189707254% = USD 318,970.73

ES = -0.001 + 0.02*0.1031356404/0.05
   = 0.04025425616 = 4.025425616% = USD 402,542.56
```

Rounding tolerance: USD 0.10 for this Normal example. Both estimates describe the same one-session horizon. No annualised volatility or square-root-of-252 multiplier belongs in this calculation.

## Part D: simulation and actual comparison

Run:

```bash
uv run --locked python commands/run_risk.py
uv run --locked pytest tests/test_risk.py -q
uv run --locked pytest -q
uv run --locked ruff check .
```

Open the printed folder's `risk_report.md` and `risk_estimates.csv`.

1. Confirm the default report has 18 estimates: 3 portfolios x 3 methods x 2 confidence levels.
2. Confirm all rows use the same close date, lookback, one-session horizon and USD 10 million NAV.
3. Pick one row: verify `var_usd = var_percent / 100 * reference_nav`; repeat for ES.
4. Check `portfolio_weights.csv`: baseline must be exactly 40% SPY / 60% AGG; each optimized allocation must sum to 100% and satisfy the policy constraints. If you have run `commands/run_optimisation.py` on the same snapshot and settings, compare against its `candidate_weights.csv` too. `commands/run_risk.py` fits the weights directly and does not create the performance-backtest files.
5. Compare Monte Carlo with Parametric. Small differences are expected because both use the same Normal distribution but one uses finite random draws. Read the standard-error columns; a seed makes the output repeatable, not exact.
6. Run the same command again: its values should be unchanged in the same environment. The automatic tests separately check repeatability and convergence within simulation error.
7. At 99%, find the historical tail warning: 1,000 observations provide only ten effective tail observations. Explain why this is weaker evidence than a large historical tail sample.

## Human review record

Use this worked guide while doing your own check. For Part A, the SPY loss is
`0.4 * 2% = 0.8%` of the portfolio and the AGG gain is `0.6 * 0.5% = 0.3%`;
the net loss is `0.5%`, or USD 50,000. For Part B, count positions 1–100:
position 95 is 9.4%, and the five observations beyond it average 9.7%.
Position 99 is 9.8%, with 9.9% beyond it. For Part C, substitute the given
mean, volatility, `z`, and `phi(z)` into the two formulas above; your USD
answers should be within USD 0.10 of the printed results.

For Part D, an existing run to inspect is
`output/risk/20261023T102523Z-0d40a885/f574e740a9af/`.
Its report has 18 rows, as of the 2026-10-22 close, using 1,000 returns,
one session, and USD 10 million per allocation. For example, its baseline
historical 95% row gives `0.6989432875642% / 100 * 10,000,000 = USD
69,894.33` VaR and `1.0059038656689% / 100 * 10,000,000 = USD
100,590.39` ES. The baseline weights are 40% SPY and 60% AGG. The
minimum-volatility weights are about 14.27% SPY, 60% AGG, 18.08% GLD,
and 7.64% XLK; the maximum-Sharpe weights are about 12.15% SPY, 60%
AGG, 17.85% GLD, and 10% XLK. Check exact figures and constraints in
the CSV before marking your own review complete.

Suggested answers to rewrite in your own words after understanding them:

- A loss can exceed VaR because VaR marks a percentile, not a maximum.
  At 95% confidence, losses beyond that cutoff can occur in roughly 5%
  of sessions under a calibrated model. ES estimates the average loss in
  that worst 5%, so it gives a sense of how severe those exceedances are.
- Gaussian Monte Carlo and Parametric estimates should be close because
  both use the same estimated mean and covariance and assume Normal
  returns. Monte Carlo approximates the result with 200,000 random draws;
  finite sampling explains small differences. A fixed seed makes those
  draws repeatable, but it does not remove model uncertainty.
- The 99% historical ES here uses only about 10 of 1,000 observations.
  One unusual day can move its average materially, so that estimate is
  less stable than one based on a much larger tail sample.

Assistant-run automated check on 2026-10-24: focused risk tests **30 passed**,
full suite **69 passed**, and Ruff **passed**. These results verify the code
in this workspace; they do not replace your independent calculation or
review. Write your own run results below if you execute the commands.

- Reviewer name: Mahinsa Kuruppu
- Review date: 24 Oct 2026
- Calculator/spreadsheet/paper used: Calculator and Paper
- Part A matched: Yes
- Part B matched: Yes
- Part C matched within rounding tolerance: Yes
- Part D rows/settings and USD scaling checked: Yes
- Snapshot and risk run folder reviewed: Yes
- Automated commands and actual results:

Read risk_report.md and complete docs/final/05-risk-models/03-manual-risk-check.md.
..............................                                           [100%]
30 passed in 1.09s
.....................................................................    [100%]
69 passed in 1.39s
All checks passed!

- Discrepancies and corrections:
- In your own words:
Why can a loss exceed VaR?
What additional information does ES provide?
**Draft for reviewer to confirm:** VaR is a loss cutoff, not the largest possible loss. For example, a 95% one-day VaR can be exceeded on some days. ES tells us the average loss on the worst 5% of days, so it shows how serious losses beyond VaR may be.
- In your own words:
Why should Gaussian Monte Carlo and Parametric estimates be close?
**Draft for reviewer to confirm:** Both methods use the same estimated average returns and covariance and assume Normal returns. The parametric method calculates from a formula, while Monte Carlo approximates the same result using random scenarios. Their results should therefore be close, with small differences from the finite number of simulations.
- Reviewer initials/sign-off: KAD

Record only checks actually performed. Completing this worksheet verifies examples and interpretation; model calibration and portfolio suitability need later validation.
