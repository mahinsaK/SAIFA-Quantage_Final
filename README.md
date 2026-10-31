# SAIFA — Quant Edge 1.0 Final Challenge

Research dashboard and investment committee materials for a proposed USD 10 million conservative university endowment portfolio.

## Start here: run the app from a fresh clone

**Run commands from the repository root** (the folder containing `app.py` and `data/LATEST`). You need Python **3.11, 3.12 or 3.13**. Choose **one** launch method below; the individual research commands later in this README are not needed to open the app.

If you have not cloned the repository yet:

```bash
git clone https://github.com/mahinsaK/SAIFA-Quantage_Final.git
cd SAIFA-Quantage_Final
```

### Option A — uv

If `uv` is installed, this is the complete launch command:

```bash
uv run --locked python commands/run_judge_app.py
```

`uv` installs the locked Python dependencies into its project environment and then starts the launcher. A separate `uv sync` step is unnecessary.

### Option B — Python and pip, without uv

With Python 3.11–3.13 and pip available, this is the complete launch command:

```bash
python run_with_pip.py
```

If `python` selects a different version, use `python3.11 run_with_pip.py` on macOS/Linux or `py -3.11 run_with_pip.py` on Windows. The script creates `.venv-pip`, installs the pinned packages from `requirements-pip.txt` and starts the same launcher. You do not need to activate the environment or install packages separately.

**Open the local URL printed in the terminal** (usually `http://127.0.0.1:8501`). Leave the terminal running while using the app; press Ctrl+C to stop it.

The first launch can take several minutes because it creates missing results, walk-forward forecasts and PDFs. Later launches verify and reuse them. Installing Python packages needs internet access on a new machine. The research preparation reads the **included frozen market snapshot** and does not download new market data.

The launcher also prepares the annual portfolio experiment and optional **Research lab**. If the research-lab stage fails, the core app still opens and the lab shows its reason and rebuild command.

The launcher is `commands/run_judge_app.py`. It verifies or rebuilds the app bundle, committee evidence and submission PDFs before starting `app.py`. You do not need to run `run_data.py`, `run_app_data.py`, `run_submission.py` or `streamlit run app.py` first.

## Find your way around the repository

| Path | Purpose |
|---|---|
| `app.py` | Streamlit entry point used by the launcher. |
| `commands/run_judge_app.py` | One-command preparation and app launch for `uv`. |
| `run_with_pip.py`, `requirements-pip.txt` | One-command pip alternative and pinned runtime packages. |
| `pyproject.toml`, `uv.lock` | Project package and locked `uv` dependencies. |
| `src/saifa/dashboard/` | The five original pages, separate Research lab page, controls and verified data loading. |
| `src/saifa/models/research/` | Experimental allocations, robustness, dynamic volatility, spending and implementation analyses. |
| `src/saifa/application/`, `models/`, `domain/`, `data/`, `reporting/` | Pipelines, calculations, result types, snapshot handling and reports. All are inside `src/saifa/`. |
| `data/snapshots/`, `data/inflation/`, `data/LATEST` | Tracked frozen ETF/rate snapshot, CPI overlay and selected snapshot ID. These are included in a clone. |
| `output/` | Generated app bundle, tables, charts and PDFs. Ignored by Git; recreated by the launcher. |
| `docs/final/` | Numbered methodology, results and human-review worksheets. |
| `tests/` | Automated tests; see `.github/workflows/ci.yml` for CI. |

The final-round app runs independently of the earlier screening project.

## What the app contains

The sidebar has the five original pages—**Portfolio**, **Risk comparison**, **Backtesting**, **Stress analysis** and **Assumptions**—plus a separate **Research lab** page. The original pages show portfolio, confidence, VaR method and backtest-date selectors. Research lab hides those selectors and uses its own controls in the main area; returning to an original page restores previous choices.

- **Portfolio:** preset 40% SPY / 60% AGG baseline versus constrained minimum-volatility and maximum-Sharpe candidates, performance, drawdown, efficient frontier, ETF correlations and purchasing power. **Annual strategy** adds a separately labelled annual re-optimisation experiment with past-only trailing-five-year fits, yearly target audits and costed validation/evaluation comparisons.
- **Risk comparison:** one-session VaR and Expected Shortfall at a common USD 10 million reference NAV. Historical, Parametric Normal, Gaussian Monte Carlo and EVT estimates retain their model-specific limitations. The frozen sample supports 90% EVT at its empirical threshold boundary; unavailable cases show a reason.
- **Backtesting:** dated forecasts, exceptions, Kupiec and Christoffersen checks, and eligible 99% Basel traffic lights. Changing the date range recalculates the displayed statistics.
- **Stress analysis:** historical crisis replays, a proposed hypothetical joint shock, asset risk contributions and funded-transfer sensitivity.
- **Research lab:** six retrospective experiments with their own controls and source evidence.
- **Assumptions:** data coverage, costs, model failures and information still needed before an investment decision.

The **Research lab** page has six visible research topics: allocations, stability, changing risk, spending, income and costs. Each has separate controls, verified outputs, a plain-language question and collapsible methodology. Spending displays withdrawal success, real-capital preservation and the stricter after-spending growth test together; dated risk models share a same-range comparison table. Retrospective experiments retain failed checks and missing-input reasons. The main risk selectors and committee materials continue to describe the original three frozen candidates. See the [research methodology, measured findings and manual review](docs/final/12-research-lab/01-research-methodology.md).

The calculations use different horizons and accounting: portfolio performance is **monthly rebalanced after trading costs**; VaR/ES uses **one-session fixed target exposures**; crisis replays hold **fixed initial units without rebalancing, costs or withdrawals**. The two optimised allocations were fitted using data through 2018, so their 2008 replays are retrospective scenarios. The 40/60 baseline is preset.

Some VaR backtests reject and all three portfolios exceed the **proposed** 15% crisis drawdown review level in 2008 and 2022. The committee recommendation is a research draft that defers implementation; it is not a client-approved allocation. The CPI comparison is observed **before withdrawals** through September 2026. Spending illustrations use separate, assumed inflation and payment rules.

The annual experiment is retrospective because those historical periods were already viewed. It uses the same construction limits and trading costs, but changes both estimation history and update frequency. Existing risk, stress, spending and committee outputs still describe the original frozen candidates; they are not adaptive-strategy validation. See the [Phase 11 methodology and manual review](docs/final/11-annual-reoptimisation/01-adaptive-methodology.md).

## Submission files

The launcher creates these files under `output/pdf/<snapshot-id>/`:

| File | Purpose |
|---|---|
| `investment-report.pdf` | Required 7–15-page investment report. |
| `executive-tear-sheet.pdf` | Separate one-page executive summary. |
| `committee-recommendation.pdf` | One-page committee decision memo. |
| `submission-manifest.json` | Snapshot, file hashes, page counts and approval status. |

`data/LATEST` identifies the snapshot used by the app and report. The generated `output/` folder is **not tracked by Git**, so a new clone rebuilds it. Include the final PDFs in the actual submission package or upload them separately; repository source alone does not include those generated PDFs.

Before submission, the team must verify the final numbers and PDFs, approve or revise the proposed stress scenario and recommendation, record actual human review, check judge access to the GitHub repository and confirm the submission route and cutoff time. The supplied deadline date is **31 October 2026**; its exact time and timezone have not been confirmed here.

## Developer and reproduction commands

The launch commands above are enough to view the app. Use the individual commands below only when developing or rebuilding a specific stage. They use the frozen snapshot by default.

| Task | Command |
|---|---|
| Prepare only the verified app data bundle | `uv run --locked python commands/run_app_data.py` |
| Regenerate committee evidence and PDFs after the bundle exists | `uv run --locked python commands/run_submission.py` |
| Rebuild only the optional research lab after the bundle exists | `uv run --locked python commands/run_research.py` |
| Rebuild only the annual portfolio experiment after the bundle exists | `uv run --locked python commands/run_adaptive.py` |
| Rebuild one research stage | See [command reference](commands/README.md) for data, portfolio, optimisation, risk, EVT, backtesting and stress runners. |
| Run automated tests | `uv run --locked pytest -q` |
| Check lint | `uv run --locked ruff check .` |

Downloading a fresh market dataset is a separate, explicit `run_data.py --download` action. It is not part of launching the app and would create a different snapshot.

## Documentation and review

Start with the [final documentation index](docs/final/README.md). The [requirements checklist](docs/final/01-planning/01-requirements-checklist.md) maps the challenge brief to evidence; the [client investment policy](docs/final/01-planning/02-client-investment-policy.md) labels team-proposed assumptions. The [AI-use log](docs/final/01-planning/03-ai-use-log.md) and [manual app worksheet](docs/final/09-streamlit-app/03-manual-app-check.md) record disclosure and checks. Each numbered phase has its own methodology, result evidence and human-review record.

Human arithmetic checks and software tests do not approve a risk model, scenario or investment. Check the dated worksheets for what has actually been reviewed and what remains open.
