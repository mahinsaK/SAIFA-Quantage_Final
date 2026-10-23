# Portfolio construction and performance methodology

Version 0.1 | 23 October 2026

## Sample discipline

The common return history is divided chronologically:

- Development: 19 November 2004 to 31 December 2018. Expected returns and covariance are estimated here only.
- Validation: 2 January 2019 to 31 December 2021. Candidate diagnostics are reported without refitting.
- Final evaluation: 3 January 2022 to 22 October 2026. Frozen candidates are compared with the 40/60 baseline without refitting.

The split is a research decision, not an organiser requirement. It prevents 2022-2026 outcomes from determining candidate weights. Arithmetic daily means and sample covariance are annualised by 252. Historical mean returns are highly uncertain and are not forecasts or guarantees.

## Construction

SciPy SLSQP solves two candidates:

- Minimum volatility minimizes annual portfolio variance.
- Maximum Sharpe maximizes `(expected return - risk-free rate) / volatility`.

The risk-free input is the average annualised lagged DGS3MO daily accrual in the development sample. Both candidates are long-only, fully invested and follow the policy draft: AGG at least 40%; each ETF at most 60%; total equities at most 50%; GLD at most 20%; XLE and XLK each at most 10% and together at most 15%. The efficient frontier repeats minimum-variance optimization across 25 feasible target returns.

Candidate weights are frozen after development estimation. Evaluation uses the same monthly close rebalancing and exact self-financing 10-basis-point gross trading cost as the baseline. The first evaluation date is an allocation date; reported daily ratios omit that one-time allocation row while wealth metrics retain its funded cost.

## Performance measures

- Sharpe: annualised arithmetic portfolio return minus annualised risk-free return, divided by annualised volatility.
- Sortino: annualised excess return divided by annualised downside deviation of excess returns.
- Beta: covariance of portfolio and SPY excess returns divided by variance of SPY excess returns.
- Treynor: annualised excess return divided by beta.
- Jensen alpha: annualised daily CAPM intercept using SPY as the market proxy.
- Information ratio: annualised active return relative to the costed 40/60 baseline divided by annualised tracking error.
- Maximum drawdown: worst peak-to-trough decline in compounded evaluation returns.
- Calmar: annualised geometric return divided by the absolute maximum drawdown.

SPY is an incomplete market proxy for a global mixed-asset portfolio. Arithmetic annualisation is used for CAPM-style ratios; portfolio wealth annualisation remains geometric. An undefined denominator produces an undefined ratio rather than a fabricated zero. The baseline's information ratio is undefined because it is compared with itself and has zero tracking error.

## Reproduction

```bash
uv run --locked python run_optimisation.py
uv run --locked pytest tests/test_optimisation.py -q
```

Generated evidence is written under `output/optimisation/<snapshot-id>/`. Human checks are in [manual-optimisation-check.md](manual-optimisation-check.md).
