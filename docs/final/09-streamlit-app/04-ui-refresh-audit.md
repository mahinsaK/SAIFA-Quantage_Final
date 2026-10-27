# UI refresh audit — comparison branch

**27 October amendment:** Earlier statements below that equality at the EVT threshold is unsupported describe the previous implementation. The [boundary update](../06-evt/04-boundary-update.md) supports equality, preserves below-boundary/failed cases, and records the reviewer-reported completion of the new boundary worksheet on 27 October 2026. Earlier signed records are unchanged.

Branch: `feat/committee-ui-refresh`. This is a presentation-only experiment against the same verified frozen outputs. The five-page navigation, controls, financial calculations, limitations, and unavailable states remain in scope.

## Current architecture

- `app.py` calls `saifa.dashboard.app`; `startup.py` sets page presentation and `sidebar.py` owns the five-page navigation and global selectors.
- `render.py` dispatches to the five views in `views.py`; `decision.py` verifies and displays the optional committee evidence.
- The dashboard loader verifies manifests, file hashes and matching snapshots before a view receives data. Date-range backtests are recalculated from dated forecasts in `selections.py`. Widget reruns do not download data or refit models.
- `output/app` and `output/decision` are generated from the included snapshot. They are evidence inputs, not UI-owned calculations.

## Main UX problems observed

1. The Portfolio page opens with a long decision/spending section. The three investment candidates are not compared together until deeper on the page.
2. Financial amounts in several grids expose unnecessary decimal precision. Dense audit tables compete with the main results.
3. Risk Comparison begins with one selected result, so the three-portfolio context is easy to miss.
4. Stress opens with marginal contribution tables before the crisis outcome, even though a committee first needs the loss and its implication.
5. The Assumptions page is a long text scroll. Details are important, but the most material limitations need a short visible summary and the rest can be opened on demand.
6. Chart colours and table presentation are specified in separate view functions; the same portfolio should have a stable colour where portfolios are compared.

## Design approach

- Lead with the conditional decision, concise scenario caveat, candidate comparison and risk outcome; keep interpretation and source detail reachable in expanders.
- Use native Streamlit controls, responsive metric containers, simple tables and charts, and the central `.streamlit/config.toml` theme. No custom CSS or new visual dependency.
- Use stable colours for selected-portfolio and risk charts from one presentation module, consistent units, accessible chart descriptions and labels. The three-line growth chart retains the original Streamlit automatic palette by team preference. Numerical values come only from verified output tables.
- Keep warnings for failed checks, stress breaches, retrospective 2008 weights, unsupported EVT 90%, absent CPI and pending human approval visible in the relevant context.

## Acceptance checks

All five pages should render; portfolio/confidence/method/date/severity controls should still change the correct results; displayed values should match source tables; no dataset or model code should change; full tests and lint should pass. Human browser and narrow-screen visual acceptance remain separate from headless checks.

## Branch verification — 26 October 2026

- The real frozen snapshot rendered all five pages in Streamlit AppTest without exceptions. The baseline portfolio comparison's ending value matched the verified optimisation CSV; the risk page displayed all three portfolios, and 90% EVT remained unavailable. Backtesting and crisis comparison tables rendered from the current controls.
- Existing selector/date/severity tests and the full suite passed: **196 tests**. Ruff lint, changed-file formatting and `git diff --check` passed.
- The branch launcher prepared matching committee evidence and started on localhost port 8502; its health endpoint returned `ok`. An isolated archive of committed `main` prepared and started separately on port 8503. The six decision CSVs and seven optimisation CSVs in those copies were byte-identical.
- No analytical model, data-acquisition, risk estimate or portfolio accounting file was edited. This does not verify visual layout or mobile behaviour. A team member should compare the two local URLs at desktop and narrow widths, review chart labels and table scrolling, then decide whether to keep the branch. No merge or human sign-off is recorded here.
