# Quant Edge 1.0 - Final Challenge

A new project for the Serendib University Endowment Fund competition mandate: construct and evaluate a USD 10 million portfolio with a conservative focus on capital preservation, income and real growth.

## Current status

The data foundation and 40% SPY / 60% AGG baseline are implemented. The baseline compares buy-and-hold, monthly rebalancing without costs, and monthly rebalancing with 10 bps charged on buys plus sells. Human accounting validation is still pending.

Optimised portfolio construction, CAPM, advanced risk models and the Streamlit app are not yet implemented. Policy numbers remain proposed research assumptions, not client-supplied limits or validated investment recommendations.

- [Requirements checklist](docs/final/requirements-checklist.md): 40 tracked requirements with brief page references and acceptance evidence, open decisions and the delivery schedule.
- [Client investment policy draft](docs/final/client-investment-policy.md): mandate, proposed horizon/objective, allocation constraints, risk review levels and decision rules.
- [Data methodology](docs/final/data-methodology.md): sources, cleaning rules, financial conventions, limitations and code map.
- [Data milestone evidence](docs/final/data-milestone.md): observed coverage, checks and remaining review work.
- [AI assistance log](docs/final/ai-use-log.md): generated components and actual validation status.
- [Baseline methodology](docs/final/baseline-methodology.md): exact accounting, metrics and limitations.
- [Baseline milestone](docs/final/baseline-milestone.md): frozen-data results and completed automated evidence.
- [Manual accounting check](docs/final/manual-accounting-check.md): independent worksheet and expected answers for team sign-off.

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

Final submission deadline: **31 October 2026**, as supplied by the team. Exact cutoff time, timezone and submission route still need confirmation. Internal completion target: **30 October 2026**.

## Relationship to the screening project

This workspace starts the final round independently. The earlier project is an archive/reference, not a runtime dependency. Keep its submitted results and Git history intact. Reuse individual components only after checking their suitability against the final brief; do not assume old assets, weights, model results or conclusions transfer to the final mandate.

The earlier project was located at the following local path on 23 October 2026:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Initial_Challenge/SAIFA`

The final brief was located at:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Final_Challenge/Quant edge 1.0 Final Challenge 1.pdf`

These paths are provenance notes for the team's machine, not portable dependencies.

## Next implementation milestone

Complete the named human reviews for data flags and the manual accounting worksheet. Then implement Markowitz construction, the efficient frontier, CAPM and remaining institutional KPIs, comparing candidate portfolios with this frozen baseline under consistent dates and costs.

## Team review

Read the checklist and policy together. Assign actual owners/reviewers, explain the assumptions in your own words, evaluate their feasibility on development data, and freeze the policy/model-selection rules before final out-of-sample evaluation. Record AI assistance and genuine human validation as work progresses.
