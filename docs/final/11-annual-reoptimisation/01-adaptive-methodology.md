# Annual portfolio re-optimisation experiment

30 October 2026. Retrospective research extension; human review pending. Existing frozen allocations and the proposed committee decision are retained.

## Research question and design

Can a specified annual target-updating rule improve the observed return/risk/cost trade-off relative to the existing frozen portfolios? This design was added after viewing the validation and evaluation history. Past-only fitting prevents mechanical look-ahead, but it does not turn this extension into a new untouched out-of-sample experiment.

The annual candidates use the preceding five **complete calendar years** of daily simple ETF returns and aligned lagged risk-free returns. Five years is a research design choice, not a proven optimum; no lookback sweep or winner selection is performed. At least 1,000 training rows are required, and January-to-December boundary coverage must be present. Inputs come from the verified frozen data products. No data is downloaded, filled, or fabricated.

For example, 2022 targets use 2017-01-01 inclusive to 2022-01-01 exclusive; the audit records actual observed first/last training sessions. No 2022 return or rate can affect that year's targets. The annual optimiser reuses the existing arithmetic means, sample covariance, annualisation, minimum-variance/maximum-Sharpe objectives and all construction limits. Risk-free returns are averaged and annualised within the same training window. Numerical solver weight-sum roundoff is recorded, normalised to one, and policy-validated before execution; estimated statistics are recomputed for those funded weights.

The original frozen candidates use the full pre-2019 development sample. This comparison therefore changes both estimation history and target-update frequency. It cannot isolate the causal effect of annual refitting alone. A matched-window, initially frozen control would be a separate follow-up study.

## Execution and accounting

- A new target is implemented at the **close of the first observed trading session each year**. On later annual updates, the old holdings earn that session's price return before the target change. The model assumes close execution with proportional costs; actual order timing, slippage and market impact remain simplified.
- Between annual updates, month-end rebalances restore that year's targets; weights drift between trades. Re-optimisation changes targets; monthly rebalancing restores targets.
- Costs are the existing 10 bps on **gross buys plus sells**, including opening funding and annual changes. Annual/monthly events on the same date execute once. Costs are funded internally; no external cash or borrowing is introduced.
- The first date of each comparison is an allocation close, matching the original engine: there is no earned return before buying. Initial invested NAV is `capital / (1+c)`.
- Validation (2019-01-02–2021-12-31) and evaluation (2022-01-03–2026-10-22) each start independently with USD 10m. They are not spliced into a single funded track record. Evaluation starts with freshly fitted past-only 2022 targets and a fresh initial cost.
- All strategies use reinvested adjusted-price distributions and no withdrawals. Whole-period wealth includes initial funding costs. Volatility/Sharpe omit the opening allocation return as in the original performance module; funded-NAV drawdown retains initial capital as a peak.

Annual changes can cause high turnover. The shared self-financing solver now brackets NAV after costs with `V*(1-c)/(1+c)` and `V`. The lower bound covers a complete rotation, whose gross traded amount can exceed the starting NAV. The old bracket `V/(1+c)` did not cover every full-rotation solution. A hand-checkable test exercises both zero and nonzero fees. The three original frozen evaluation ending NAVs reproduced exactly on this snapshot after this correction.

Missing history, rates, non-finite inputs or failed optimisation aborts the experiment. There is no silent last-weight or baseline fallback. A failed output manifest is not displayed.

## Published evidence and app

Run the usual app launcher, which prepares this extension after the base bundle. To rebuild just this stage:

```bash
uv run --locked python commands/run_adaptive.py
```

Outputs under `output/adaptive/<snapshot-id>/`:

- `annual_targets.csv`: both objectives, execution/training dates, observation counts, seven weights, solver information, estimated inputs/statistics and raw solver weight sum.
- `daily.csv`, `transactions.csv`: separately labelled validation/evaluation holdings, current targets, NAV, turnover, costs and annual-change events.
- `metrics.csv`: baseline, two original frozen and two annual candidates on each period, including return, volatility, drawdown, costs and Sharpe.
- `comparison.csv`: annual-minus-frozen ending wealth, annual return, volatility, drawdown-loss and trading-cost changes for each objective and period.
- `summary.json`, `manifest.json`: exact bundle binding, input/source hashes, settings, limitations and pending human status.

The loader checks output/source hashes and snapshot/policy consistency on access. The data-stage price/rate files are checked against their published hashes without rebuilding or modifying the base bundle.

Open **Portfolio → Annual strategy**. The period and objective controls affect the comparison/table/chart/audit. The global portfolio sidebar continues to describe the frozen candidates. No new strategies are added to the risk selectors.

Long explanations and the selected annual-minus-frozen narrative are grouped under **Read explanation, methodology and limitations**, collapsed by default. Controls, dates, costs, result table and chart remain visible. A short retrospective/pending-risk notice stays visible; detailed limitations remain available on demand. The training audit has its own existing expander.

## Limits and decision scope

One five-year window rule and annual cadence do not establish robustness. Annual forecasts, adaptive VaR/ES/EVT, coverage tests, risk contributions, crisis replays, CPI comparisons and spending sustainability have **not** been established for these adaptive strategies. Existing versions of those analyses remain tied to frozen candidates. The final report, tear sheet and committee recommendation remain the original frozen-candidate materials pending team review of this new research.

No human worksheet, scenario approval or investment decision is completed by this experiment.
