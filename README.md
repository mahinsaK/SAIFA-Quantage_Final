# Quant Edge 1.0 - Final Challenge

A new project for the Serendib University Endowment Fund competition mandate: construct and evaluate a USD 10 million portfolio with a conservative focus on capital preservation, income and real growth.

## Current status

The data foundation, 40% SPY / 60% AGG baseline and constrained Markowitz candidates are implemented. The baseline accounting was manually validated by Mahinsa Kuruppu on 23 October 2026; all three hand-calculated examples matched and the focused test suite passed. The optimiser produces minimum-volatility and maximum-Sharpe candidates, an efficient frontier, CAPM diagnostics and the required performance ratios with a chronological out-of-sample comparison.

Historical, Parametric Normal, correlated Gaussian Monte Carlo and EVT POT/GPD VaR/ES are implemented at 95% and 99% confidence, with an equal-USD-10m target-allocation comparison. EVT includes development/as-of diagnostics, threshold sensitivity and block-bootstrap uncertainty. Mahinsa Kuruppu completed the manual EVT arithmetic and signed off 90% as a provisional research threshold on 24 October 2026. Walk-forward forecasts, Kupiec coverage, Christoffersen independence and the historical Basel traffic light are now implemented; their human review is pending. Some model/period tests reject, and the reports retain those results. Risk contributions, stress analysis and the Streamlit app remain outstanding. Policy numbers remain proposed research assumptions, not client-supplied limits or validated investment recommendations. Human review records are maintained separately in the linked worksheets.

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
- [EVT methodology](docs/final/evt-methodology.md): threshold rationale, GPD formulas and uncertainty.
- [EVT milestone](docs/final/evt-milestone.md): frozen-data results and diagnostic interpretation.
- [Manual EVT check](docs/final/manual-evt-check.md): independent calculations and threshold-review record.
- [Backtesting methodology](docs/final/backtesting-methodology.md): forecast timing, statistical definitions, missing-data handling and limitations.
- [Backtesting milestone](docs/final/backtesting-milestone.md): frozen results, rejections and automated verification evidence.
- [Manual backtest check](docs/final/manual-backtest-check.md): timing, likelihood and transition-count exercises for actual team review.

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

## Run the EVT study

```bash
uv run --locked python run_evt.py
uv run --locked pytest tests/test_evt.py -q
```

Open `evt_report.md` in the printed `output/evt/<snapshot>/<settings-hash>/` folder. It includes six diagnostic charts, threshold sensitivity, six EVT estimates and 95% bootstrap intervals. `risk_comparison.csv` contains all four methods on identical inputs. The default 90% loss threshold is a prespecified and provisionally reviewed research rule; current-window results never automatically change it. Unsupported confidence/threshold combinations and unreliable fits are marked unavailable, not zero. The signed manual review is in `manual-evt-check.md`.

Optional research settings: `--as-of YYYY-MM-DD`, `--lookback 1000`, `--threshold 0.90`, `--confidence 0.95 0.99`, `--bootstrap 200`, `--block-length 10`, `--seed 314159`. A 90% forecast confidence is at the default threshold boundary and is explicitly unsupported. Changing a setting creates a separate run folder. Always check `status.json` and row-level warnings.

Final submission deadline: **31 October 2026**, as supplied by the team. Exact cutoff time, timezone and submission route still need confirmation. Internal completion target: **30 October 2026**.

## Relationship to the screening project

This workspace starts the final round independently. The earlier project is an archive/reference, not a runtime dependency. Keep its submitted results and Git history intact. Reuse individual components only after checking their suitability against the final brief; do not assume old assets, weights, model results or conclusions transfer to the final mandate.

The earlier project was located at the following local path on 23 October 2026:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Initial_Challenge/SAIFA`

The final brief was located at:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Final_Challenge/Quant edge 1.0 Final Challenge 1.pdf`

These paths are provenance notes for the team's machine, not portable dependencies.

## Run walk-forward VaR backtesting

```bash
uv run --locked python run_backtest.py
uv run --locked pytest tests/test_backtesting.py -q
```

This offline runner uses the frozen snapshot, development-only allocations and rolling 1,000-return windows. It forecasts each next exchange session at 95%/99% for all four methods, with 200,000 date-seeded Normal simulations. The default covers 2019–22 October 2026 and may take several minutes. Read `backtest_report.md` in the printed `output/backtest/<snapshot>/<settings-hash>/` folder, then complete the manual worksheet. Require `status.json` to say `complete`.

```bash
uv run --locked python run_backtest.py --start 2022-01-01 --end-exclusive 2026-10-23
```

Changing the forecast range does not change a shared date's forecasts. Missing or insufficient evidence is explicitly unavailable. Validation and evaluation results remain separate; Basel colours require 250 complete sessions at 99%. This tests one-day losses of fixed target exposures at USD 10m, not the monthly-rebalanced NAV after costs. The evaluation is retrospective because earlier final-period results have already been viewed. Non-rejection or a green latest window is not a safety guarantee; these tests do not validate ES severity.

## Next implementation milestone

Complete the backtesting worksheet and any remaining risk interpretation. Next implement marginal/component VaR and ES contributions, historical crisis replays and a team-designed hypothetical stress scenario. Carry the backtest's coverage/clustering limitations into the investment decision; do not choose or retune a model simply to make the evaluation tests pass.

## Team review

Read the checklist and policy together. Assign actual owners/reviewers, explain the assumptions in your own words, evaluate their feasibility on development data, and freeze the policy/model-selection rules before final out-of-sample evaluation. Record AI assistance and genuine human validation as work progresses.