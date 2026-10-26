# Quant Edge 1.0 - Final Challenge

A new project for the Serendib University Endowment Fund competition mandate: construct and evaluate a USD 10 million portfolio with a conservative focus on capital preservation, income and real growth.

## Current status

The data foundation, 40% SPY / 60% AGG baseline and constrained Markowitz candidates are implemented. The baseline accounting was manually validated by Mahinsa Kuruppu on 23 October 2026; all three hand-calculated examples matched and the focused test suite passed. The optimiser produces minimum-volatility and maximum-Sharpe candidates, an efficient frontier, CAPM diagnostics and the required performance ratios with a chronological out-of-sample comparison.

Historical, Parametric Normal, correlated Gaussian Monte Carlo and EVT POT/GPD VaR/ES are implemented at 95% and 99% confidence, with an equal-USD-10m target-allocation comparison. EVT includes development/as-of diagnostics, threshold sensitivity and block-bootstrap uncertainty. Mahinsa Kuruppu completed the manual EVT arithmetic and signed off 90% as a provisional research threshold on 24 October 2026. Walk-forward forecasts, Kupiec coverage, Christoffersen independence and the historical Basel traffic light are now implemented; their human review is pending. Some model/period tests reject, and the reports retain those results. Normal VaR/ES contributions, Historical ES contributions, funded allocation sensitivity, historical crisis replays and hypothetical stress analysis are now implemented; their manual review and scenario approval remain pending. The Streamlit app now presents all five research pages with working portfolio, confidence, method, date-range and severity controls. Automated verification is complete; browser visual review remains open. Policy numbers remain proposed research assumptions, not client-supplied limits or validated investment recommendations. Human review records are maintained separately in the linked worksheets.

The [documentation index](docs/final/README.md) lists every file by phase. Start with the [requirements checklist](docs/final/01-planning/01-requirements-checklist.md), then use the numbered folders from planning through the Streamlit app. Within each phase, `01` explains the method, `02` records results, and `03` holds the review worksheet (planning uses checklist, policy and AI log).

## Open the Streamlit app

From a fresh checkout, with `uv` installed, use one command:

```bash
uv run --locked python commands/run_judge_app.py
```

Open the local URL printed by Streamlit. The launcher verifies existing results and prepares anything missing from the included frozen snapshot before opening the app. The first run can take several minutes because it builds all 90/95/99% forecasts, committee evidence and PDFs. Later runs reuse verified results. Dependency installation may require internet access; preparation does **not** download market data.

For separate preparation and launch steps while developing:

```bash
uv run --locked python commands/run_app_data.py
uv run --locked python commands/run_submission.py
uv run --locked streamlit run app.py
```

After installation, the packaged equivalents are available from the project
root: `uv run --locked saifa-dashboard-data`, `uv run --locked saifa-data`,
and `uv run --locked saifa-risk`.

The five pages cover portfolio performance, side-by-side risk, date-sensitive backtesting, stress analysis and limitations. Sidebar dates affect backtesting only. The app recomputes tests from the selected dated forecasts and retains missing forecasts. EVT at 90% is explicitly unavailable under the current 90% threshold; no higher-confidence value is substituted. Basel colours require 250 complete sessions at 99% within the selected period.

If outputs are absent, incomplete or modified, the app explains the issue and shows the preparation command. The one-command launcher prepares those outputs automatically. It follows `data/LATEST`; keep it aligned with the intended frozen submission snapshot. Generated outputs remain ignored by Git, so a fresh checkout rebuilds them.

See the [app methodology](docs/final/09-streamlit-app/01-app-methodology.md), [verification evidence](docs/final/09-streamlit-app/02-app-milestone.md) and [manual browser check](docs/final/09-streamlit-app/03-manual-app-check.md).

## Run the data pipeline

Install uv, then run from this directory:

```bash
uv sync --locked
uv run --locked python commands/run_data.py
```

The included snapshot is reused. The pipeline does not contact Yahoo/FRED unless explicitly requested:

```bash
uv run --locked python commands/run_data.py --download --start 2004-01-01 --end 2026-10-23
```

Run verification:

```bash
uv run --locked pytest -q
uv run --locked ruff check .
```

Read the generated quality_report.md and quality_flags.csv in `output/data/<snapshot-id>/`. `data/LATEST` identifies the last complete acquisition; `status.json` separately records whether preparation succeeded. Raw snapshots are retained; failed acquisitions never replace the latest pointer. A successful build does not mean flagged market events have been reviewed by the team.

Build the baseline portfolio from the same frozen snapshot:

```bash
uv run --locked python commands/run_portfolio.py
```

Results are generated under `output/portfolio/<snapshot-id>/`. This command does not download new data. It reproduces the data outputs first, then builds the three baseline strategies.

Build the constrained Markowitz candidates and out-of-sample comparison:

```bash
uv run --locked python commands/run_optimisation.py
```

Results are generated under `output/optimisation/<snapshot-id>/`. Candidate weights use development data through 2018; 2019-2021 is validation and 2022 onward is the final evaluation period.

Build the one-day VaR/ES comparison from the frozen snapshot:

```bash
uv run --locked python commands/run_risk.py
```

This rebuilds data and fits candidate allocations offline using the shared development-only estimator; it does not run or require the full performance backtest. It compares all three allocations at the same USD 10 million NAV using the last 1,000 daily return observations through the latest close, 95%/99% confidence, and 200,000 joint Normal scenarios with seed 42. Open `risk_report.md` in the printed `output/risk/<snapshot-id>/<settings-hash>/` folder. The estimates describe target holdings over the next trading session; they do not include future trading costs or drifted portfolio holdings.

Optional settings (confidence uses fractions):

```bash
uv run --locked python commands/run_risk.py --as-of 2026-10-22 --lookback 1000 --confidence 0.90 0.95 0.99
uv run --locked pytest tests/test_risk.py -q
```

Different settings create separate risk folders; repeating identical settings reproduces that folder. Always require `status.json` to say `complete` before using its results.

## Run the EVT study

```bash
uv run --locked python commands/run_evt.py
uv run --locked pytest tests/test_evt.py -q
```

Open `evt_report.md` in the printed `output/evt/<snapshot>/<settings-hash>/` folder. It includes six diagnostic charts, threshold sensitivity, six EVT estimates and 95% bootstrap intervals. `risk_comparison.csv` contains all four methods on identical inputs. The default 90% loss threshold is a prespecified and provisionally reviewed research rule; current-window results never automatically change it. Unsupported confidence/threshold combinations and unreliable fits are marked unavailable, not zero. The signed review is in the [manual EVT check](docs/final/06-evt/03-manual-evt-check.md).

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
uv run --locked python commands/run_backtest.py
uv run --locked pytest tests/test_backtesting.py -q
```

This offline runner uses the frozen snapshot, development-only allocations and rolling 1,000-return windows. It forecasts each next exchange session at 95%/99% for all four methods, with 200,000 date-seeded Normal simulations. The default covers 2019–22 October 2026 and may take several minutes. Read `backtest_report.md` in the printed `output/backtest/<snapshot>/<settings-hash>/` folder, then complete the manual worksheet. Require `status.json` to say `complete`.

```bash
uv run --locked python commands/run_backtest.py --start 2022-01-01 --end-exclusive 2026-10-23
```

Changing the forecast range does not change a shared date's forecasts. Missing or insufficient evidence is explicitly unavailable. Validation and evaluation results remain separate; Basel colours require 250 complete sessions at 99%. This tests one-day losses of fixed target exposures at USD 10m, not the monthly-rebalanced NAV after costs. The evaluation is retrospective because earlier final-period results have already been viewed. Non-rejection or a green latest window is not a safety guarantee; these tests do not validate ES severity.

## Run contributions and stress analysis

```bash
uv run --locked python commands/run_stress.py
uv run --locked pytest tests/test_stress.py -q
```

Open `stress_report.md` in the printed `output/stress/<snapshot>/<settings-hash>/` folder. The offline run provides Normal marginal/component VaR and ES, Historical ES attribution, feasible/infeasible funded 1 percentage point transfers, three crisis replays and joint-shock severity sensitivity. Use `--as-of YYYY-MM-DD`, `--lookback 1000` or `--confidence 0.95 0.99` for explicit research settings. Require `status.json` to say `complete` and inspect row-level warnings.

The replays use USD 10m, fixed initial allocations and drifting buy-and-hold holdings without fees or withdrawals. They are retrospective scenarios; 2018-fitted weights were not available in 2008. The hypothetical one-session ETF shocks are proposed assumptions requiring team approval. All three portfolios exceed the proposed 15% drawdown review level in 2008 and 2022, even though their current-window Normal/Historical 99% ES estimates are below the separate 2% one-day level. Neither result is a safety guarantee.

See the [methodology](docs/final/08-contributions-stress/01-contributions-stress-methodology.md), [milestone evidence](docs/final/08-contributions-stress/02-contributions-stress-milestone.md) and [manual worksheet](docs/final/08-contributions-stress/03-manual-stress-check.md). Implementation is complete; human review and the investment decision remain open.

## Committee evidence and submission documents

After preparing the app bundle, run:

```bash
uv run --locked python commands/run_submission.py
```

This offline command produces a verified decision extension and the investment report, executive tear sheet and one-page committee memo in `output/pdf/<snapshot>/`. The Portfolio page presents the same decision and selected-portfolio spending figures. Rebuild after source changes. Missing/stale evidence is explained rather than displayed. Generated PDFs remain Git-ignored: include the rebuilt files in the submission package.

The proposed recommendation defers implementation and retains minimum volatility only as a conditional discussion candidate. All candidates breach crisis review levels. The snapshot has no CPI; observed real-growth attainment stays unavailable. Spending uses explicitly hypothetical 0%, 2% and 4% constant-inflation assumptions, never substituted for observed data. See the [decision methodology](docs/final/10-investment-decision/01-decision-methodology.md), [verification evidence](docs/final/10-investment-decision/02-decision-milestone.md) and [manual team review](docs/final/10-investment-decision/03-manual-decision-check.md).

## Next submission milestone

Complete the backtesting and contributions/stress worksheets, review the proposed hypothetical scenario and decide how to respond to breached stress review levels. Complete the app browser review and independently evaluate the draft committee recommendation, report and tear sheet. Confirm actual spending/client needs, missing CPI evidence, final PDF versions and judge access. Carry the backtest's coverage/clustering limitations into the investment decision; do not choose or retune a model simply to make the evaluation tests pass.

## Team review

Read the checklist and policy together. Assign actual owners/reviewers, explain the assumptions in your own words, evaluate their feasibility on development data, and freeze the policy/model-selection rules before final out-of-sample evaluation. Record AI assistance and genuine human validation as work progresses.
