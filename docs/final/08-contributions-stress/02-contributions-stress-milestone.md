# Contributions and stress milestone

Implementation and automated verification: **complete, 25 October 2026**. Human calculation, scenario approval and final investment interpretation: **pending** in the [manual worksheet](03-manual-stress-check.md).

## Reproduce

```bash
uv run --locked python commands/run_stress.py
uv run --locked pytest tests/test_stress.py -q
uv run --locked pytest -q
uv run --locked ruff check .
```

Default snapshot: `20261023T102523Z-0d40a885`. Run folder: `output/stress/20261023T102523Z-0d40a885/200356ee3cbe/`. Attribution uses 1,000 returns from 27 October 2022 through 22 October 2026, forecasting the 23 October session at USD 10m. Allocations are fitted through 31 December 2018. The metadata records source hashes and the Git working state; this milestone was verified before its commit.

## Evidence

- 28 focused tests; 151 full-suite tests passed. Ruff lint passed. All eight added/modified Python files pass formatting checks. Repository-wide formatting also identified six pre-existing files outside this phase; those were left unchanged.
- The offline frozen-data run completed; two consecutive unchanged runs produced identical hashes for all 22 output files, including five charts and provenance metadata.
- All 18 contribution totals agree with the matching pre-existing Normal/Historical risk estimates to fraction tolerance 1e-12. Signed asset components reconcile to risk totals, historical terminal losses and hypothetical losses.
- 126 asset attribution rows, 756 sizing rows (including infeasible transfers), nine complete historical scenario/portfolio rows and nine hypothetical portfolio/severity rows were generated. Historical expected sessions per allocation are 253, 22 and 251.
- Tests include independent Normal derivatives and hand examples, zero holdings, hedge offsets, deterministic versus undefined gradients, fractional empirical tail mass and ties, policy feasibility, initial-close/peak-based drawdown, bankruptcy, missing crisis sessions, future-data isolation and flags for allocations estimated after the replayed period.
- Charts and the generated report were inspected for labels, units, assumptions and agreement with the numerical tables. Generated data/reports remain ignored by Git.

## Results to interpret

Current-window one-session 99% risk, USD:

| Portfolio | Normal VaR | Normal ES | Historical ES |
|---|---:|---:|---:|
| 40/60 baseline | 108,131.90 | 124,487.34 | 153,489.10 |
| Minimum volatility | 107,358.83 | 123,689.97 | 148,188.93 |
| Maximum Sharpe | 109,220.32 | 125,836.64 | 149,926.07 |

All these ES estimates are below the separate proposed 2% (USD 200,000) one-day review level. Historical ES at 99% has only ten observations' effective tail mass and should not be treated as precise or stable.

Maximum drawdown in the selected buy-and-hold replay windows:

| Portfolio | Calendar 2008 | March 2020 | Calendar 2022 |
|---|---:|---:|---:|
| 40/60 baseline | 21.744% | 14.668% | 18.947% |
| Minimum volatility | 16.319% | 11.750% | 17.476% |
| Maximum Sharpe | 16.354% | 11.717% | 17.683% |

**All three exceed the proposed 15% review level in 2008 and 2022.** Lower losses than the baseline do not establish that the candidates meet the mandate. Calendar windows are not full-crisis peak-to-trough histories. The 2008 replay uses actual 2008 returns: the baseline 40/60 allocation is preset, while the two optimised allocations were estimated later. None is evidence of an actual 2008 investment track record.

Base hypothetical one-session losses are 8.400% (USD 840,000) for baseline, 7.412% (USD 741,181.57) for minimum volatility and 7.572% (USD 757,191.49) for maximum Sharpe. At 1.5-times severity, all exceed the proposed 10% scenario-loss review level. Severity is an assumption, not an estimated probability.

## Remaining human work and next implementation

1. Complete Parts A–E and the reviewer record in the manual worksheet.
2. Approve or revise the proposed scenario narrative and ETF shocks, recording reasoning. The current scenario is an AI-assisted draft, not a completed team decision.
3. Explain the stress breaches alongside the earlier coverage/clustering failures. Decide whether the allocation, mandate assumptions or review levels need reconsideration; do not relax limits solely to obtain a pass.
4. Integrate results into Streamlit, then prepare the investment committee recommendation, report and tear sheet with consistent figures and limitations. Those deliverables are outside this implemented phase.
