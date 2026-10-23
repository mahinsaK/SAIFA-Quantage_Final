# Quant Edge 1.0 - Final Challenge

A new project for the Serendib University Endowment Fund competition mandate: construct and evaluate a USD 10 million portfolio with a conservative focus on capital preservation, income and real growth.

## Current status

The data foundation, 40% SPY / 60% AGG baseline and constrained Markowitz candidates are implemented. The baseline accounting was manually validated by Mahinsa Kuruppu on 23 October 2026; all three hand-calculated examples matched and the focused test suite passed. The optimiser produces minimum-volatility and maximum-Sharpe candidates, an efficient frontier, CAPM diagnostics and the required performance ratios with a chronological out-of-sample comparison.

Historical, Parametric Normal and correlated Gaussian Monte Carlo VaR/ES are implemented at 95% and 99% confidence, with an equal-USD-10m target-allocation comparison. EVT, formal VaR backtesting and the Streamlit app remain outstanding. Policy numbers remain proposed research assumptions, not client-supplied limits or validated investment recommendations. Human review records are maintained separately in the linked worksheets.

- [Requirements checklist](docs/final/requirements-checklist.md): 40 tracked requirements with brief page references and acceptance evidence, open decisions and the delivery schedule.
- [Client investment policy draft](docs/final/client-investment-policy.md): mandate, proposed horizon/objective, allocation constraints, risk review levels and decision rules.
- [Data methodology](docs/final/data-methodology.md): sources, cleaning rules, financial conventions, limitations and code map.
- [Data milestone evidence](docs/final/data-milestone.md): observed coverage, checks and remaining review work.
- [AI assistance log](docs/final/ai-use-log.md): generated components and actual validation status.
- [Baseline methodology](docs/final/baseline-methodology.md): exact accounting, metrics and limitations.
- [Baseline milestone](docs/final/baseline-milestone.md): frozen-data results and completed automated evidence.
- [Manual accounting check](docs/final/manual-accounting-check.md): completed independent accounting worksheet and reviewer record.
- [Optimisation methodology](docs/final/optimisation-methodology.md): sample split, constraints, estimators and KPI definitions.
- [Optimisation milestone](docs/final/optimisation-milestone.md): frozen weights and out-of-sample results.
- [Manual optimisation check](docs/final/manual-optimisation-check.md): constraint, covariance and CAPM calculations for team sign-off.
- [Data quality review](docs/final/data-quality-review.md): grouped flags and the required human inspection record.
- [Risk methodology](docs/final/risk-methodology.md): one-day loss definitions, shared inputs, timing and model limitations.
- [Risk milestone](docs/final/risk-milestone.md): observed VaR/ES comparisons and verification evidence.
- [Manual risk check](docs/final/manual-risk-check.md): hand examples and reviewer worksheet.

## Run the data pipeline

Install uv, then run from this directory:

```bash
uv sync --locked
uv run --locked python run_data.py
```

The included snapshot is reused. The pipeline does not contact Yahoo/FRED unless explicitly requested:

```bash
uv run --locked python run_data.py --download --start 2004-01-01 --end 2026-10-23
```

Run verification:

```bash
uv run --locked pytest -q
uv run --locked ruff check .
```

Read the generated quality_report.md and quality_flags.csv in `output/data/<snapshot-id>/`. `data/LATEST` identifies the last complete acquisition; `status.json` separately records whether preparation succeeded. Raw snapshots are retained; failed acquisitions never replace the latest pointer. A successful build does not mean flagged market events have been reviewed by the team.

Build the baseline portfolio from the same frozen snapshot:

```bash
uv run --locked python run_portfolio.py
```

Results are generated under `output/portfolio/<snapshot-id>/`. This command does not download new data. It reproduces the data outputs first, then builds the three baseline strategies.

Build the constrained Markowitz candidates and out-of-sample comparison:

```bash
uv run --locked python run_optimisation.py
```

Results are generated under `output/optimisation/<snapshot-id>/`. Candidate weights use development data through 2018; 2019-2021 is validation and 2022 onward is the final evaluation period.

Build the one-day VaR/ES comparison from the frozen snapshot:

```bash
uv run --locked python run_risk.py
```

This rebuilds data and fits candidate allocations offline using the shared development-only estimator; it does not run or require the full performance backtest. It compares all three allocations at the same USD 10 million NAV using the last 1,000 daily return observations through the latest close, 95%/99% confidence, and 200,000 joint Normal scenarios with seed 42. Open `risk_report.md` in the printed `output/risk/<snapshot-id>/<settings-hash>/` folder. The estimates describe target holdings over the next trading session; they do not include future trading costs or drifted portfolio holdings.

Optional settings (confidence uses fractions):

```bash
uv run --locked python run_risk.py --as-of 2026-10-22 --lookback 1000 --confidence 0.90 0.95 0.99
uv run --locked pytest tests/test_risk.py -q
```

Different settings create separate risk folders; repeating identical settings reproduces that folder. Always require `status.json` to say `complete` before using its results.

Final submission deadline: **31 October 2026**, as supplied by the team. Exact cutoff time, timezone and submission route still need confirmation. Internal completion target: **30 October 2026**.

## Relationship to the screening project

This workspace starts the final round independently. The earlier project is an archive/reference, not a runtime dependency. Keep its submitted results and Git history intact. Reuse individual components only after checking their suitability against the final brief; do not assume old assets, weights, model results or conclusions transfer to the final mandate.

The earlier project was located at the following local path on 23 October 2026:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Initial_Challenge/SAIFA`

The final brief was located at:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Final_Challenge/Quant edge 1.0 Final Challenge 1.pdf`

These paths are provenance notes for the team's machine, not portable dependencies.

## Next implementation milestone

Complete the risk worksheet and any outstanding named human reviews. Next implement EVT diagnostics and threshold sensitivity, then walk-forward VaR coverage/independence tests and stress analysis. The current VaR/ES comparison is an as-of estimate, not coverage-validation evidence.

## Team review

Read the checklist and policy together. Assign actual owners/reviewers, explain the assumptions in your own words, evaluate their feasibility on development data, and freeze the policy/model-selection rules before final out-of-sample evaluation. Record AI assistance and genuine human validation as work progresses.
