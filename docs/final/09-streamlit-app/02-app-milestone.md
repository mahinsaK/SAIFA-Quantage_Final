# Streamlit app milestone

25 October 2026: implementation for U01–U07 is complete, with the explicit 90% EVT unsupported state permitted by the task. Final human UI review and the wider competition deliverables remain open.

## Automated and local verification

- Streamlit 1.66.1 and its dependencies were installed and locked. Existing numerical package versions were retained.
- 19 focused dashboard tests and the 170-test full suite passed. Ruff lint and formatting checks for new Python files passed.
- Tests cover absent/corrupt/incomplete bundles, wrong snapshot, paths outside the project, changed raw inputs, hash-consistent but invalid USD units, stale cache rejection, control-dependent risk selection, missing forecasts, equality at VaR, period boundaries, shortened Basel windows and unavailable 90% EVT.
- Streamlit AppTest exercised all five pages with synthetic test fixtures and the real frozen submission snapshot. Portfolio/confidence/method/date/severity changes were exercised. Requests-based network access was blocked in the UI fixtures; no acquisition code runs when the app opens.
- The offline preparation command built the complete app bundle. It contains 36 risk rows (three portfolios × four methods × three confidences), 70,668 dated forecast rows across 1,963 sessions, 27 attribution totals, 189 asset contributions and 1,134 funded-transfer rows. Unsupported EVT rows remain present.
- The actual server launched on `http://127.0.0.1:8501`; its health endpoint returned `ok`.
- Browser/Computer Use permission was unavailable in the agent session. No browser screenshot or visual-layout sign-off is claimed. Complete the [manual app check](03-manual-app-check.md) in a browser.

## Verified examples from the frozen snapshot

Snapshot: `20261023T102523Z-0d40a885`.
Bundle: `output/app/20261023T102523Z-0d40a885/bundle.json`.

| Selection | Observed app result |
|---|---|
| Baseline performance, 2022 onward | Ending NAV USD 12,448,401.99; cumulative return 24.48%; annualised return 4.67%; drawdown 18.78% |
| Baseline Historical risk, 99% | VaR USD 110,505.04; ES USD 153,489.10 |
| Baseline Historical risk, 90% | VaR USD 51,173.71 |
| EVT risk/backtest, 90% | Unavailable due to the 90% threshold boundary; missing forecasts retained |
| Baseline Historical 99%, full evaluation | 11 exceptions / 1,206 sessions; expected 12.06 |
| Same selection, 24 Oct 2025–22 Oct 2026 | 1 exception / 250 sessions; expected 2.50 |
| Baseline 2008 replay | Maximum drawdown 21.74%; USD 2,191,458.25 from its relevant peak |
| Baseline 2022 replay | Terminal loss USD 1,508,312.92; maximum drawdown 18.95% |
| Baseline base / 1.5-times hypothetical shock | USD 840,000 / USD 1,260,000 loss; 8.4% / 12.6% |

The performance and stress drawdown figures differ because their dates, initial holdings and rebalancing/cost conventions differ; the app labels both. The values are research outputs, not evidence of approval or a promised return.

## Remaining work

Complete browser layout/readability and manual control checks, finish the outstanding earlier worksheet reviews, interpret policy breaches, and prepare the final recommendation, report and tear sheet. Hosting and GitHub judge-access checks are not completed by this local implementation. No existing human worksheet or team scenario decision was marked complete.
