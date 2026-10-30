# Command reference

To **run the app from a fresh clone**, follow the [root README quick start](../README.md#start-here-run-the-app-from-a-fresh-clone). The launcher prepares missing outputs automatically; the commands below are for individual rebuilds and research work.

Run these commands from the repository root. With `uv`, prefix a Python script with `uv run --locked python`. For example:

```bash
uv run --locked python commands/run_judge_app.py
```

| Script | Purpose |
|---|---|
| `run_judge_app.py` | Verify or build the frozen app bundle, committee evidence, PDFs and annual experiment; then launch Streamlit. This is the app quick-start command. |
| `run_data.py` | Rebuild data preparation from the included frozen snapshot. A new market download requires the explicit `--download` option. |
| `run_portfolio.py` | Rebuild the 40/60 baseline portfolio outputs. |
| `run_optimisation.py` | Rebuild constrained Markowitz candidates and performance comparisons. |
| `run_risk.py` | Rebuild one-session VaR/ES comparisons. |
| `run_evt.py` | Rebuild EVT estimates and diagnostics. |
| `run_backtest.py` | Rebuild walk-forward forecasts and coverage/independence checks. |
| `run_stress.py` | Rebuild crisis replays, hypothetical shocks and risk contributions. |
| `run_app_data.py` | Prepare only the verified app data bundle. |
| `run_submission.py` | Prepare committee evidence and submission PDFs from an existing verified app bundle. |
| `run_adaptive.py` | Compare annual trailing-five-year re-optimisation with frozen candidates using the verified offline bundle. |

For a pip-only computer, run `python run_with_pip.py` from the repository root. It installs pinned runtime dependencies and calls `run_judge_app.py`. See the [root README](../README.md) for Python version requirements and platform-specific commands.

The numbered [final documentation](../docs/final/README.md) explains each model's settings, outputs, warnings and human checks. Generated outputs are under `output/` and are ignored by Git.
