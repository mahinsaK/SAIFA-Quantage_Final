# Manual one-day VaR and Expected Shortfall check

Status: **human review pending**.

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
uv run --locked python run_risk.py
uv run --locked pytest tests/test_risk.py -q
uv run --locked pytest -q
uv run --locked ruff check .
```

Open the printed folder's `risk_report.md` and `risk_estimates.csv`.

1. Confirm the default report has 18 estimates: 3 portfolios x 3 methods x 2 confidence levels.
2. Confirm all rows use the same close date, lookback, one-session horizon and USD 10 million NAV.
3. Pick one row: verify `var_usd = var_percent / 100 * reference_nav`; repeat for ES.
4. Check `portfolio_weights.csv`: baseline must be exactly 40% SPY / 60% AGG; each optimized allocation must sum to 100% and satisfy the policy constraints. If you have run `run_optimisation.py` on the same snapshot and settings, compare against its `candidate_weights.csv` too. `run_risk.py` fits the weights directly and does not create the performance-backtest files.
5. Compare Monte Carlo with Parametric. Small differences are expected because both use the same Normal distribution but one uses finite random draws. Read the standard-error columns; a seed makes the output repeatable, not exact.
6. Run the same command again: its values should be unchanged in the same environment. The automatic tests separately check repeatability and convergence within simulation error.
7. At 99%, find the historical tail warning: 1,000 observations provide only ten effective tail observations. Explain why this is weaker evidence than a large historical tail sample.

## Human review record

- Reviewer name:
- Review date:
- Calculator/spreadsheet/paper used:
- Part A matched:
- Part B matched:
- Part C matched within rounding tolerance:
- Part D rows/settings and USD scaling checked:
- Snapshot and risk run folder reviewed:
- Automated commands and actual results:
- Discrepancies and corrections:
- In your own words: Why can a loss exceed VaR? What additional information does ES provide?
- In your own words: Why should Gaussian Monte Carlo and Parametric estimates be close?
- Reviewer initials/sign-off:

Record only checks actually performed. Completing this worksheet verifies examples and interpretation; model calibration and portfolio suitability need later validation.
