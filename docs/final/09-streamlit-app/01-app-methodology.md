# Streamlit app: design and calculation boundaries

Implemented 25 October 2026. The app presents the research candidates and evidence; it does not approve an allocation or complete human review records.

## Launch and offline preparation

From the project root:

```bash
uv sync --locked
uv run --locked python run_app_data.py
uv run --locked streamlit run app.py
```

Dependency installation needs access to the package registry on first setup. The preparation command and app use the local snapshot identified by `data/LATEST`; they do not acquire market data. Preparation invokes the existing optimisation, EVT/risk comparison, stress and backtesting pipelines. It can take several minutes. Later launches need only the Streamlit command.

`run_app_data.py --snapshot <id>` prepares an explicitly selected snapshot, but the app always follows `data/LATEST`; these must identify the same intended submission snapshot. The default submission snapshot is `20261023T102523Z-0d40a885`. Do not change the pointer merely to hide a failed acquisition.

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
- Risk comparison uses the same 1,000-return as-of window, fixed target exposures, one-session horizon and USD 10m reference NAV for all four methods. The app reads the existing EVT pipeline's comparison, including Normal, Historical and Gaussian Monte Carlo estimates.
- The preparation command requests all three confidence levels. EVT at 90% remains unavailable under the provisional 90% POT threshold. Both the estimate and its forecasts retain the unavailable status and explanation. No 95%/99% estimate is relabeled and no threshold is retuned to fill the gap.
- All model/date combinations remain in the prepared forecast dataset, including failed/unsupported fits. Selection reindexes to the complete XNYS calendar, recomputes strict `loss > VaR` exceptions and calls the existing `kupiec_test`, `christoffersen_test` and `basel_traffic_light` functions. A missing day stays missing; no adjacent dates are joined across it.
- Validation (2019–2021) and evaluation (2022 onward) remain separate even when a chosen range crosses their boundary. Coverage and independence use each selected period. Basel uses at most the latest 250 sessions within that period and within the selected range, and is unavailable unless exactly 250 complete 99% forecasts exist. All-missing forecasts do not display a misleading zero-exception success.
- Stress paths use the existing fixed-initial-allocation buy-and-hold replays without fees/withdrawals. The 2008 replay is explicitly retrospective. The selected hypothetical shock and multiplier retain their assumptions and signed asset offsets. Funded sizing checks are sensitivity results, not recommendations.
- Undefined ratios, tail estimates and gradients remain unavailable. Missing baseline columns for never-held ETFs can be displayed as zero holdings; missing held-asset weights are not replaced by zero.

## Code map

| File | Responsibility |
|---|---|
| `app.py` | Entry point, sidebar, verified cache and page routing |
| `run_app_data.py` | Explicit offline preparation command |
| `src/application/dashboard_pipeline.py` | Reuses the pipelines and publishes the app bundle |
| `src/domain/dashboard.py` | Bundle/result types, labels and required output contract |
| `src/dashboard/data.py` | Integrity checks, loading and cross-stage validation |
| `src/dashboard/selections.py` | Pure selection and date-range statistical recalculation |
| `src/dashboard/views.py` | Portfolio, risk, backtesting, stress and limitations pages |
| `.streamlit/config.toml` | Shared light theme and disabled usage telemetry |
| `tests/test_dashboard.py` | Independent examples, input integrity and Streamlit control tests |

The existing financial model implementations are reused. Streamlit is pinned by `uv.lock`; no paid service is required. The UI uses native charts/tables, explicit units, selected-result downloads and an audit expander for detailed records.

## Practical limits and review

The app uses a prepared snapshot and does not provide live trading, live risk monitoring or automatic portfolio approval. Changing a backtest range changes the statistical evidence being viewed, not the original forecasts or model settings. Repeatedly selecting favourable ranges is not independent model validation. Previously viewed evaluation data remain retrospective.

The selected risk levels are proposals, not client-approved rules. Inflation-adjusted spending sustainability, liquidity during forced sales and a final investment decision remain outside this phase. Human review records are neither inferred from successful tests nor rewritten by the app. Browser visual review remains a team check; automated Streamlit tests verify application output/control behaviour but cannot establish that every screen layout is readable on every device.

Implementation references: [Streamlit AppTest](https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest) and [Streamlit caching](https://docs.streamlit.io/develop/api-reference/caching-and-state/st.cache_data).
