# Project commands

These scripts are the command-line entry points for rebuilding the project's
data products and analysis results. Run them from the repository root with
`uv run --locked python`.

| Command | Purpose |
| --- | --- |
| `commands/run_data.py` | Acquire or rebuild a frozen market-data snapshot |
| `commands/run_portfolio.py` | Build the baseline portfolio outputs |
| `commands/run_optimisation.py` | Build constrained optimisation candidates |
| `commands/run_risk.py` | Build risk comparison outputs |
| `commands/run_evt.py` | Build extreme-value-theory outputs |
| `commands/run_backtest.py` | Build rolling backtest outputs |
| `commands/run_stress.py` | Build stress and contribution outputs |
| `commands/run_app_data.py` | Prepare the verified data bundle used by Streamlit |

For example:

```bash
uv run --locked python commands/run_app_data.py
```

The scripts resolve project data and cache paths from their location. Invoke
them from the repository root so Python can resolve the local `src` package.

`uv run --locked python commands/run_submission.py` builds committee evidence, spending sensitivity and PDF submission drafts from the already prepared app bundle, offline. See Phase 10 documentation.

`uv run --locked python commands/run_judge_app.py` verifies or builds all local outputs from the frozen snapshot and launches Streamlit with one command. First preparation may take several minutes; it does not fetch market data.

For a computer with Python 3.11–3.13 and pip but no uv, run `python run_with_pip.py` from the project root. It installs the pinned app dependencies into `.venv-pip` and starts the same launcher. See the project README for the manual pip commands.
