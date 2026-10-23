# One-day VaR and Expected Shortfall milestone

Implemented and automatically checked on 23 October 2026. Human risk review remains pending.

Snapshot: `20261023T102523Z-0d40a885`. Default risk run: `f574e740a9af`.

## Scope and settings

- Portfolios: 40/60 baseline and both frozen development-estimated Markowitz target allocations.
- Reference NAV: USD 10 million for each allocation.
- As of: close on 22 October 2026; forecast session: 23 October 2026.
- Window: 1,000 observed daily returns, 27 October 2022 through 22 October 2026.
- Horizon: one session of fixed holdings; market P&L before future trading costs.
- Historical, Parametric Normal and correlated Gaussian Monte Carlo VaR and ES, each at 95% and 99%.
- Monte Carlo: 200,000 joint asset scenarios, explicit PCG64 seed 42.

## Observed 99% comparison

| Allocation | Method | VaR | ES | VaR USD | ES USD |
|---|---|---:|---:|---:|---:|
| 40/60 baseline | Historical | 1.1051% | 1.5349% | 110,505.04 | 153,489.10 |
| 40/60 baseline | Parametric Normal | 1.0813% | 1.2449% | 108,131.90 | 124,487.34 |
| 40/60 baseline | Monte Carlo Normal | 1.0819% | 1.2444% | 108,187.57 | 124,441.08 |
| Minimum volatility | Historical | 1.1654% | 1.4819% | 116,544.91 | 148,188.93 |
| Minimum volatility | Parametric Normal | 1.0736% | 1.2369% | 107,358.83 | 123,689.97 |
| Minimum volatility | Monte Carlo Normal | 1.0732% | 1.2313% | 107,319.25 | 123,132.77 |
| Maximum Sharpe | Historical | 1.1579% | 1.4993% | 115,786.48 | 149,926.07 |
| Maximum Sharpe | Parametric Normal | 1.0922% | 1.2584% | 109,220.32 | 125,836.64 |
| Maximum Sharpe | Monte Carlo Normal | 1.0914% | 1.2537% | 109,141.57 | 125,372.78 |

All 18 rows, including 95%, are in the generated report. In this window the Normal models estimate smaller 99% ES than empirical history for each allocation. That comparison does not establish which model is calibrated; only ten observations contribute to the 99% historical tail. Optimized portfolios do not dominate every measure: for example, their historical 99% VaR is higher than the baseline's while their historical 99% ES is lower. No final risk-model or allocation selection is made from these results.

## Verification

- 30 risk-specific automated cases and 69 tests overall passed; Ruff and `git diff --check` passed.
- Independent small-number checks cover loss sign, holdings P&L, empirical quantile rank, integer/fractional ES tails, ties, Normal formulas and USD scaling.
- A perfectly negatively correlated two-asset example verifies that simulated covariance is retained and that offsetting exposures cancel risk.
- Fixed-seed simulation agrees with analytical Normal VaR/ES within five conditional Monte Carlo standard errors in the test sample and every row of the full-data comparison. This tests implementation, not model adequacy.
- Tests cover zero risk, 90% support, confidence ordering, invalid inputs, insufficient history, future-data exclusion, and the allocation-estimation cutoff.
- Pipeline tests cover provenance, 18-row output, deterministic reruns, separate settings folders and failure status.
- All eight risk output files were byte-identical across two consecutive full-data builds with unchanged code/settings/environment.

Review corrections: fractional confidence labels now preserve values such as 95.5%; the risk pipeline uses the shared development-only allocation estimator rather than requiring the full performance backtest and future evaluation-period data. The shared estimator also uses the configured annualisation for the development risk-free rate. Regression tests exercise an early snapshot ending on 2 January 2019, real candidate fits with modified future returns/rates, aligned development rates and the non-default annualisation. Default candidate weights and all 18 risk rows remained byte-identical after these changes.

The generated summary records Git revision and working-tree state, source hashes, dependency lock, package versions, manifest and allocation hashes. The implementation was checked in an uncommitted working tree based on revision `a4d8c23`; the source hashes identify the precise code. After committing, rerun to associate evidence with that commit.

## Reproduce and review

```bash
uv run --locked python run_risk.py
uv run --locked pytest tests/test_risk.py -q
```

Open `output/risk/20261023T102523Z-0d40a885/f574e740a9af/risk_report.md` and complete [manual-risk-check.md](manual-risk-check.md). See [risk-methodology.md](risk-methodology.md) for exact formulas, limitations, output meaning and reference documentation.

This milestone supplies R01-R03 implementation evidence. Human review, EVT threshold work, walk-forward coverage testing, crisis/scenario analysis and the committee decision remain outstanding. The snapshot comparison is not a loss ceiling or a backtest pass.
