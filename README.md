# Quant Edge 1.0 - Final Challenge

A new project for the Serendib University Endowment Fund competition mandate: construct and evaluate a USD 10 million portfolio with a conservative focus on capital preservation, income and real growth.

## Current status

Planning documents are ready for team review. Data acquisition, financial models, tests and the Streamlit application have not yet been implemented in this repository. Policy numbers are proposed research assumptions, not client-supplied limits or validated investment recommendations.

- [Requirements checklist](docs/final/requirements-checklist.md): 40 tracked requirements with brief page references and acceptance evidence, open decisions and the delivery schedule.
- [Client investment policy draft](docs/final/client-investment-policy.md): mandate, proposed horizon/objective, allocation constraints, risk review levels and decision rules.

Final submission deadline: **31 October 2026**, as supplied by the team. Exact cutoff time, timezone and submission route still need confirmation. Internal completion target: **30 October 2026**.

## Relationship to the screening project

This workspace starts the final round independently. The earlier project is an archive/reference, not a runtime dependency. Keep its submitted results and Git history intact. Reuse individual components only after checking their suitability against the final brief; do not assume old assets, weights, model results or conclusions transfer to the final mandate.

The earlier project was located at the following local path on 23 October 2026:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Initial_Challenge/SAIFA`

The final brief was located at:

`/Users/mahinsak/Documents/Competitions/⚡ Quant Edge 1.0 /Final_Challenge/Quant edge 1.0 Final Challenge 1.pdf`

These paths are provenance notes for the team's machine, not portable dependencies.

## Next implementation milestone

Build the data foundation: adjusted prices for SPY, EFA, EEM, AGG, GLD, XLE and XLK; a documented FRED risk-free proxy; a frozen data snapshot; calendar and data-quality checks; and correct log/simple return handling. Establish a simple benchmark before adding portfolio optimisation and advanced risk models.

## Team review

Read the checklist and policy together. Assign actual owners/reviewers, explain the assumptions in your own words, evaluate their feasibility on development data, and freeze the policy/model-selection rules before final out-of-sample evaluation. Record AI assistance and genuine human validation as work progresses.
