# Phase 10 implementation and verification evidence

**28 October CPI amendment:** The historical statements below that CPI was unavailable describe the earlier submission version. A separate frozen FRED CPIAUCSL overlay now supports the observed **before-withdrawal** 3% real-growth check through 30 September 2026. The [methodology](01-decision-methodology.md) and [new unsigned review worksheet](04-observed-cpi-review.md) distinguish that measured period from hypothetical spending and the proposed ten-year objective. Original market snapshot and prior signed records are unchanged; client spending and team approval remain pending.

The rebuilt `observed_real.csv` records annual real growth of **0.6782%** (40/60), **2.5418%** (minimum volatility) and **2.7133%** (maximum Sharpe); all are below the proposed 3% objective in the observed period. The report is now **13 pages**, with separate one-page tear sheet and committee memo. On 28 October the full suite passed **218 tests**, Ruff lint passed, and formatting passed for all nine changed Python files. The four pre-existing whole-repository format failures are in untouched optimisation/performance files. Real-snapshot Streamlit AppTest showed matching observed values for all three portfolio selections and no exceptions on Assumptions; the temporary localhost server returned HTTP 200 from `/_stcore/health`. All PDF pages were rendered for visual inspection, including the new CPI page. Browser/device visual acceptance and independent team CPI review remain open.

**27 October amendment:** Earlier statements below that equality at the EVT threshold is unsupported describe the previous implementation. The [boundary update](../06-evt/04-boundary-update.md) supports equality, preserves below-boundary/failed cases, and records the reviewer-reported completion of the new boundary worksheet on 27 October 2026. Earlier signed records are unchanged.

26 October 2026. Implementation complete; **independent human review and the final investment decision remain pending**. No committee/client policy approval, scenario approval or human worksheet was completed by the agent.

## Deliverables

Snapshot: `20261023T102523Z-0d40a885`. Evaluation: 3 January 2022 to 22 October 2026. The original numerical models and frozen raw files are unchanged.

- A conditional recommendation to defer implementation, retaining minimum volatility as a research discussion candidate. The report preserves coverage/clustering failures and crisis breaches rather than claiming safety.
- Nine spending scenarios: three existing portfolios times 0/2/4% assumed constant annual inflation. Four anniversary payments per scenario. Actual CPI-based wealth and actual real-objective attainment remain unavailable.
- Verified decision extension: comparison table, 72 separate validation/evaluation backtest summaries, 72 latest-window traffic-light records, spending summaries, 10,854 daily scenario rows and 36 dated payments. Unsupported EVT 90% stays unavailable.
- Portfolio-page decision/spending section plus updated assumptions text; all five navigation pages retained.
- `output/pdf/<snapshot>/investment-report.pdf`: **12 pages**.
- `output/pdf/<snapshot>/executive-tear-sheet.pdf`: **1 page**.
- `output/pdf/<snapshot>/committee-recommendation.pdf`: **1 page**.
- Matching readable Markdown drafts and artifact hashes/page counts in `submission-manifest.json`.

Generated artifacts are intentionally ignored by Git. Recreate them using `uv run --locked python commands/run_submission.py` after the existing app-data preparation. A separate source-code/policy/lockfile digest binds the decision to the verified base bundle. Rebuilding after source changes is required.

## Observed spending evidence (hypothetical, not forecasts)

Assumed inflation 2%; net first annual payment USD 300,000, later indexed to that first payment. Four payments total USD 1,236,525.55; additional liquidation fees total USD 1,237.76 at 10 bps. No payment shortfall occurred in these historical scenarios; this is not a probability of future success.

| Portfolio | Nominal ending wealth | Scenario-real ending wealth | Annual real remaining-capital growth | Additional 3% after-spending test |
|---|---:|---:|---:|---|
| 40/60 baseline | $10,918,507.10 | $9,928,580.14 | -0.149231% | Not met |
| Minimum volatility | $11,847,609.14 | $10,773,445.10 | 1.564354% | Not met |
| Maximum Sharpe | $11,923,512.06 | $10,842,466.27 | 1.699586% | Not met |

The original policy's 3% objective is before withdrawals. In the 2% assumed-inflation case its before-spending real capital growth is 2.616553%, 4.247771%, and 4.385688% respectively. These conditional arithmetic outcomes do not resolve missing observed inflation or the client's actual ten-year spending requirement.

## Verification actually executed

- Focused `tests/test_spending.py tests/test_decision.py`: **22 passed**.
- Full `uv run --locked pytest -q`: **192 passed in 26.60 seconds**.
- `uv run --locked ruff check .`: passed.
- Spending tests cover independently hand-checkable payments, fee funding, assumed inflation, anniversary/partial-year timing, insolvency/shortfall, invalid data, exact no-spending recovery, and a separate holdings simulation with same-day rebalancing/withdrawal.
- Integrity tests reject missing/tampered decision outputs, a stale base bundle and changed source hashes. UI tests confirm the selected portfolio changes spending values while actual real-growth attainment stays unestablished.
- The full offline submission runner completed against the real snapshot. All three real portfolio selections displayed their matching spending rows in Streamlit AppTest; all five pages ran without exceptions.
- The local Streamlit server started on `127.0.0.1:8501`; its `/_stcore/health` endpoint returned `ok`.
- All 12 report pages and both one-page artifacts were rendered with Poppler and visually inspected. Page counts were independently checked with pypdf; the initial backtesting overflow was corrected. Final layouts have no observed clipping/overlap.
- No market data was downloaded. ReportLab was added to the locked dependencies for reproducible PDF generation.

AppTest and server health do not establish browser/device visual acceptance. The team's existing browser review remains open. The PDF visual inspection is an agent check, not a signed human judgment about the recommendation.

## Files and responsibilities

| File | Responsibility |
|---|---|
| `src/saifa/domain/decision.py` | Typed spending result, explicit assumptions, conditional narrative and review conditions |
| `src/saifa/models/spending.py` | Scale-consistent withdrawals, funding fees, inflation scenarios and shortfalls |
| `src/saifa/application/decision_pipeline.py` | Verified-source comparison, dated backtest recalculation, spending outputs and provenance |
| `src/saifa/dashboard/decision.py` | Extension verification and compact Portfolio-page summary |
| `src/saifa/dashboard/views.py` | Integrates the summary and clarifies scenario boundaries |
| `src/saifa/reporting/submission.py` | Shared-evidence report, tear sheet and committee memo rendering |
| `commands/run_submission.py` | Explicit offline build command |
| `tests/test_spending.py`, `tests/test_decision.py` | Accounting, source integrity, UI selection and document-generation checks |

README, requirements checklist, documentation index, AI-use log and dependency lockfile were updated. [Manual review](03-manual-decision-check.md) gives exact examples and output figures for the team to check.

## Decisions still required

Team acceptance/revision/rejection of the AI-assisted recommendation; scenario approval; actual spending amounts/dates/currency, fees and liquidity needs; CPI provenance and inflation relevance; interpretation of stress breaches and model failures; committee policy approval; completion of genuine human reviews; browser acceptance; judge-accessible repository, final artifact packaging, roster and exact submission cutoff/route. No automatic trading or actual fund-management readiness is claimed.

## One-command judge launch rehearsal - 26 October 2026

The README now leads with `uv run --locked python commands/run_judge_app.py`. The launcher verifies the frozen app bundle, decision extension and three PDFs; it reuses complete outputs and builds only missing/stale stages. It starts Streamlit bound to `127.0.0.1`.

An isolated copy with **no `.git`, `.venv`, `.cache` or generated `output/`** was created from the current workspace. Locked dependencies installed in that copy; its first run completed the full offline app analysis, 1,963 forecast sessions, decision evidence and three PDFs from the included raw snapshot. Running the single launcher command after preparation reused every artifact, started the app at `127.0.0.1:8502`, and the health endpoint returned `ok`. The ZIP case records Git revision and dirty state as unavailable while retaining source-file hashes. The 12/1/1-page PDFs generated in the clean copy are byte-identical to the rebuilt workspace PDFs.

Three new focused launcher tests and one Git-free provenance test passed. The updated full suite is **196 passed**; Ruff and formatting checks passed. The first run needed internet access for registry dependencies, with no market-data download. Actual visual browser review remains a team task: the automation browser was unavailable and native Safari inspection timed out. Judge repository access and final submission packaging have not been claimed complete.
