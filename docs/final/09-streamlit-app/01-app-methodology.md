# Streamlit app: design and calculation boundaries

Implemented 25 October 2026. The app presents the research candidates and evidence; it does not approve an allocation or complete human review records.

## Launch and offline preparation

From the project root, the judge-facing route is:

```bash
uv run --locked python commands/run_judge_app.py
```

The launcher verifies and reuses complete app, decision and PDF artifacts. It prepares missing or changed artifacts and then starts Streamlit. Dependency installation needs access to the package registry on first setup. Preparation and app use the local snapshot identified by `data/LATEST`; they do not acquire market data. Preparation invokes the existing optimisation, EVT/risk comparison, stress and backtesting pipelines and may take several minutes. For debugging, run `commands/run_app_data.py` and `commands/run_submission.py` separately before `uv run --locked streamlit run app.py`.

For a computer with Python 3.11–3.13 and pip but no uv, `python run_with_pip.py` is the second one-command route. It creates `.venv-pip`, installs the runtime packages pinned in `requirements-pip.txt` (exported from `uv.lock`), and invokes the same judge launcher. The first run needs package-registry access; subsequent runs reuse the environment if dependency files are unchanged.

`commands/run_app_data.py --snapshot <id>` prepares an explicitly selected snapshot, but the app always follows `data/LATEST`; these must identify the same intended submission snapshot. The default submission snapshot is `20261023T102523Z-0d40a885`. Do not change the pointer merely to hide a failed acquisition.

The builder publishes `output/app/<snapshot>/bundle.json` only after verification. It records exact output directories and file hashes. The app does not choose whichever settings folder happens to be newest. An incomplete bundle, missing file, wrong snapshot or changed checksum yields a visible explanation and the preparation command. Generated output remains ignored by Git. If an individual pipeline rewrites a file used by the bundle, rebuild the bundle before using the app again.

Every rerun verifies the bundle, source manifest/raw-input hashes and consumed output hashes. Parsed tables are cached using the verified manifest digest. Thus a cache hit cannot silently hide a changed or missing file. The loader also checks portfolio-policy compatibility, risk confidence/method coverage, NAV/horizon/currency consistency, candidate weights, forecast timing and key uniqueness. This verifies consistency, not the investment merits of a model.

## What the controls change

| Control | Effect |
|---|---|
| Portfolio | Selected holdings, performance summary/path, risk estimates, dated forecasts and stress results |
| Confidence: 90%, 95%, 99% | Selects estimates and forecasts computed at that exact confidence; also selects applicable contributions |
| VaR method | Selects the highlighted risk measures and the dated forecast series used for recalculated backtests; supported contribution methods follow it |
| Inclusive backtest start/end | Selects dated forecasts and recomputes coverage, independence and latest eligible Basel diagnostics |
| Historical crisis | Selects its fixed crisis window and selected portfolio path |
| Hypothetical severity | Selects the explicitly modelled joint-shock multiplier and resulting component/total loss |

The backtest date control does not alter the performance evaluation period, current as-of risk window or historical crisis definitions. The interface states this. Crisis and hypothetical scenarios have no assigned confidence probability.

## Preserved financial conventions

- Portfolio performance uses the original costed, monthly-rebalanced evaluation series. Target weights are fitted through 2018; holdings drift between rebalances. Initial USD 10m funding and gross trading both incur 10 bps costs. The opening capital is included in the underlying drawdown calculation. All three comparative paths use identical evaluation dates.
- The Portfolio page also reads the already-saved development efficient frontier and candidate estimates. Its separate ETF heatmap computes Pearson correlations from the latest 252 aligned daily simple-return rows. `simple_returns.csv` is included in the hash-verified app bundle; the heatmap is a recent descriptive diagnostic, not the optimiser covariance or a future correlation forecast.
- The observed-real-growth bars use the separate verified CPI decision table, costed evaluation NAV through 30 September 2026 and a single proposed 3% annual target. They compare portfolios over the same dates before withdrawals; the 2% inflation spending illustration remains a different, hypothetical sensitivity. No daily real-NAV line is invented across the missing October 2025 CPI month.
- Risk comparison uses the same 1,000-return as-of window, fixed target exposures, one-session horizon and USD 10m reference NAV for all four methods. The app reads the existing EVT pipeline's comparison, including Normal, Historical and Gaussian Monte Carlo estimates.
- The preparation command requests all three confidence levels. EVT includes the effective threshold boundary: VaR equals the empirical cutoff and ES uses the fitted GPD tail mean. The frozen 90% estimates and rolling forecasts use this labelled boundary case. Below-boundary confidence (including tied samples), failed fits and invalid intervals remain unavailable with reasons. No 95%/99% estimate is relabeled and no threshold is retuned. See the [boundary update](../06-evt/04-boundary-update.md).
- All model/date combinations remain in the prepared forecast dataset, including failed/unsupported fits. Selection reindexes to the complete XNYS calendar, recomputes strict `loss > VaR` exceptions and calls the existing `kupiec_test`, `christoffersen_test` and `basel_traffic_light` functions. A missing day stays missing; no adjacent dates are joined across it.
- Validation (2019–2021) and evaluation (2022 onward) remain separate even when a chosen range crosses their boundary. Coverage and independence use each selected period. Basel uses at most the latest 250 sessions within that period and within the selected range, and is unavailable unless exactly 250 complete 99% forecasts exist. All-missing forecasts do not display a misleading zero-exception success.
- The Backtesting page puts Validation, Evaluation and Full history period buttons above the results. Their dates come from the verified forecast metadata and update the same sidebar date-range state used for custom dates. The current inclusive dates are stated immediately below the buttons, and the buttons remain available if a custom range is incomplete or invalid.
- The Backtesting forecast view plots the selected dated losses and VaR as an Altair chart with client-side date zoom and pan. Hovering an exception shows its date, VaR, realised loss and excess loss; the exact exception-date table gives the same values without requiring visual inspection of small points. Both use the recalculated selection and do not change the statistical tests or rerun Python when zooming.
- The model-comparison matrix reruns those same tested backtest functions for each portfolio and VaR method at the sidebar's selected confidence and inclusive dates. It displays validation or evaluation separately and distinguishes rejected, not-rejected and unavailable cells. A non-rejection is not model approval.
- Stress paths use the existing fixed-initial-allocation buy-and-hold replays without fees/withdrawals. The 2008 replay is explicitly retrospective. The selected hypothetical shock and multiplier retain their assumptions and signed asset offsets. Funded sizing checks are sensitivity results, not recommendations.
- The cross-crisis chart reads all available historical replay summaries and marks their common proposed drawdown review level; unavailable rows retain reasons in the table. The signed ETF risk bars read supported Normal VaR/ES or Historical ES components only. Monte Carlo and EVT attribution is not silently substituted.
- Undefined ratios, tail estimates and gradients remain unavailable. Missing baseline columns for never-held ETFs can be displayed as zero holdings; missing held-asset weights are not replaced by zero.

## Code map

| File | Responsibility |
|---|---|
| `app.py` | Entry point, sidebar, verified cache and page routing |
| `commands/run_app_data.py` | Explicit offline preparation command |
| `commands/run_judge_app.py` | One-command verified preparation and local launch |
| `src/saifa/application/dashboard_pipeline.py` | Reuses the pipelines and publishes the app bundle |
| `src/saifa/domain/dashboard.py` | Bundle/result types, labels and required output contract |
| `src/saifa/dashboard/data.py` | Integrity checks, loading and cross-stage validation |
| `src/saifa/dashboard/selections.py` | Pure selection and date-range statistical recalculation |
| `src/saifa/dashboard/visual_data.py` | Validates common periods, review levels and defined chart components |
| `src/saifa/dashboard/section_navigation.py` | Portfolio section links, stable anchors and browser-side scroll feedback without a Streamlit rerun |
| `src/saifa/dashboard/views.py` | Portfolio, risk, backtesting, stress and limitations pages |
| `.streamlit/config.toml` | Shared light theme and disabled usage telemetry |
| `tests/test_dashboard.py` | Independent examples, input integrity and Streamlit control tests |
| `tests/test_dashboard_visual_data.py` | Chart-data timing, unavailable values and signed-offset checks |

The existing financial model implementations are reused. Streamlit is pinned by `uv.lock`; no paid service is required. The UI uses native charts/tables, explicit units, selected-result downloads and an audit expander for detailed records.

The Portfolio page uses a compact section bar: Summary goes to “Selected portfolio at a glance”; Performance to “Performance and holdings”; Drawdown to the selected-portfolio drawdown; Efficient frontier to the development curve; Diversification to the ETF correlation heatmap; and Purchasing power to the observed-CPI and hypothetical-spending section. Summary is pinned outside the horizontally scrolling section-link row, so it remains visible after scrolling to a later section. The committee view remains above Summary. Each destination is the native Streamlit anchor on its visible subheader, rather than a separate invisible element. The top “Portfolio performance” heading has a distinct `portfolio-page` anchor to prevent a duplicate `portfolio-performance` fragment.

The same bar covers Risk comparison (portfolio comparison, selected estimate and method comparison), Backtesting (overview, only the validation/evaluation periods present in the selected date range, the model-comparison matrix and forecast chart), and Stress analysis (crisis replay, cross-crisis portfolio comparison, joint shock and risk contributions). Assumptions has no section bar. A small Streamlit Component v2 keeps the bar fixed to the viewport while it measures its own host width, scrolls to these headings, and listens to the actual scroll container plus section intersections to update the active link. It sends no state back to Python, so link clicks do not rerun the page. The non-pinned links scroll horizontally on narrow screens, and the bar updates or unmounts as the page changes. Browser visual, fixed-position and smooth-scroll behaviour requires the manual check recorded in the app worksheet; headless AppTest verifies the configured destinations and heading anchors but does not execute the browser component.

## Practical limits and review

The app uses a prepared snapshot and does not provide live trading, live risk monitoring or automatic portfolio approval. Changing a backtest range changes the statistical evidence being viewed, not the original forecasts or model settings. Repeatedly selecting favourable ranges is not independent model validation. Previously viewed evaluation data remain retrospective.

The selected risk levels are proposals, not client-approved rules. Inflation-adjusted spending sustainability, liquidity during forced sales and a final investment decision remain outside this phase. Human review records are neither inferred from successful tests nor rewritten by the app. Browser visual review remains a team check; automated Streamlit tests verify application output/control behaviour but cannot establish that every screen layout is readable on every device.

Implementation references: [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) and [Streamlit caching](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data).
