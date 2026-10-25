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
