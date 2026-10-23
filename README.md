# Quant Edge 1.0 - Final Challenge

A new project for the Serendib University Endowment Fund competition mandate: construct and evaluate a USD 10 million portfolio with a conservative focus on capital preservation, income and real growth.

## Current status

The data foundation is implemented: explicit Yahoo/FRED acquisition, frozen snapshots, calendar and quality checks, simple/log asset returns, lagged risk-free accrual and descriptive stationarity diagnostics. The included dataset has 5,515 return observations per ETF, from 19 November 2004 through 22 October 2026. Review flags are retained for team investigation.

Portfolio construction, risk models and the Streamlit app are not yet implemented. Policy numbers remain proposed research assumptions, not client-supplied limits or validated investment recommendations.

- [Requirements checklist](docs/final/requirements-checklist.md): 40 tracked requirements with brief page references and acceptance evidence, open decisions and the delivery schedule.
- [Client investment policy draft](docs/final/client-investment-policy.md): mandate, proposed horizon/objective, allocation constraints, risk review levels and decision rules.
- [Data methodology](docs/final/data-methodology.md): sources, cleaning rules, financial conventions, limitations and code map.
- [Data milestone evidence](docs/final/data-milestone.md): observed coverage, checks and remaining review work.
- [AI assistance log](docs/final/ai-use-log.md): generated components and actual validation status.

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

Final submission deadline: **31 October 2026**, as supplied by the team. Exact cutoff time, timezone and submission route still need confirmation. Internal completion target: **30 October 2026**.

## Relationship to the screening project

This workspace starts the final round independently. The earlier project is an archive/reference, not a runtime dependency. Keep its submitted results and Git history intact. Reuse individual components only after checking their suitability against the final brief; do not assume old assets, weights, model results or conclusions transfer to the final mandate.

The earlier project was located at the following local path on 23 October 2026:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Initial_Challenge/SAIFA`

The final brief was located at:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Final_Challenge/Quant edge 1.0 Final Challenge 1.pdf`

These paths are provenance notes for the team's machine, not portable dependencies.

## Next implementation milestone

Review data flags and financial conventions, then establish the proposed 40% SPY / 60% AGG benchmark with correct portfolio-value accounting, monthly rebalancing and transaction costs. Compare return and drawdown before adding portfolio optimisation and advanced risk models. No portfolio results are claimed by the data foundation.

## Team review

Read the checklist and policy together. Assign actual owners/reviewers, explain the assumptions in your own words, evaluate their feasibility on development data, and freeze the policy/model-selection rules before final out-of-sample evaluation. Record AI assistance and genuine human validation as work progresses.
