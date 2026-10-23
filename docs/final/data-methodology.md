# Data foundation: methods and reproduction

Implemented: 23 October 2026. This module prepares asset returns and descriptive diagnostics. It does not select allocations, fit risk models or decide the final train/test split.

## Sources and settings

| Input | Source | Treatment |
|---|---|---|
| SPY, EFA, EEM, AGG, GLD, XLE, XLK | Yahoo Finance through yfinance | Daily history; explicit Adj Close and Close; actions included; auto_adjust=False, back_adjust=False, repair=False, keepna=True, rounding=False |
| DGS3MO | FRED; Board of Governors H.15 | Daily 3-month Treasury constant-maturity yield, quoted on an investment basis in annual percent |
| US session dates | exchange_calendars, XNYS | Common US-session proxy for these US-listed ETFs; holidays and special closures come from the locked calendar version |

Primary references: [yfinance settings](https://ranaroussi.github.io/yfinance/reference/api/yfinance.download.html), [DGS3MO definition](https://fred.stlouisfed.org/series/DGS3MO), [exchange_calendars](https://github.com/gerrymanoim/exchange_calendars), [statsmodels ADF](https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html).

The request starts on 1 January 2004 to obtain pre-2008 data. Start is inclusive and end exclusive. The CLI excludes today's New York session to avoid an unfinished daily bar. Dates are coverage choices, not approved model lookbacks. A different download window creates a different snapshot.

Explicit Adj Close is required. The pipeline never substitutes unadjusted Close if it is absent. Adjustment-factor jumps are flagged and source action columns retained for investigation. Using adjusted prices handles the vendor's split/dividend adjustments; it does not independently establish that every vendor adjustment is correct. Total-return history must not be interpreted as cash distribution income.

## Snapshot contract

`data/snapshots/<id>/` contains seven provider-normalised price CSVs, the original FRED CSV response and a manifest. The manifest records settings, sources, acquisition start time, Python/package versions and SHA-256 hashes. yfinance has already parsed/normalised its returned DataFrames; these files are not raw Yahoo HTTP responses.

An explicit download makes a new directory and never overwrites a previous snapshot. Incomplete acquisitions retain an error manifest and cannot be loaded. Only complete acquisitions update `data/LATEST`. That pointer means acquisition completed, not that data-quality review passed. Preparation separately records `status.json`; consume derived results only when it says `complete`.

Every offline load verifies required files and hashes. Derived summary.json records the source manifest hash, current source-code hashes, dependency-lock hash and output CSV hashes. This detects accidental changes, not malicious rewriting of a manifest. Preserve the chosen snapshot and lockfile in the submission. Provider historical revisions, adjustment changes and FRED vintage revisions are not reconstructed by this snapshot.

## Calendar and missingness policy

All seven instruments trade on US sessions even when their underlying holdings are abroad. A foreign-market holiday does not imply that a US ETF quote should be discarded. XNYS is a disclosed calendar proxy for their US listings, not a claim that every ETF is listed on the NYSE itself.

We inspect each ticker on the requested session grid. Coverage begins at the latest first valid quote across the seven ETFs. Leading unavailable sessions are counted in coverage.csv; the first downloaded quote is not independently verified as the legal inception date. Nothing is backfilled before this date.

After each ticker's first valid quote, missing session prices are blocking errors. Duplicated/unordered dates, unexpected quote dates, invalid/nonpositive/infinite prices and invalid Close fields also block processing. Prices are never interpolated or forward-filled. The pipeline therefore never disguises a multi-session movement as a one-session return. Raw inputs and available flags remain available after failure.

## Flags and review

Defaults are research screening thresholds, not statistical significance tests:

| Flag | Trigger | Default action |
|---|---|---|
| Large daily return | Absolute simple return at least 10% | Retain and review; crisis losses must not be silently removed |
| Flat run | At least five consecutive zero-return sessions | Retain; inspect quote/trading activity |
| Adjustment-factor jump | Adj Close / Close changes at least 10% | Retain; reconcile source actions |
| Volatility shift candidate | Trailing 20-session return volatility / preceding 60-session volatility at least 3 | Retain; descriptive possible regime shift, not a proven structural break |

All screening uses current/past observations only. Full-sample summaries are descriptive and must not drive selection using the eventual test period. One event can produce several flags across instruments and dates; a flag count is not a count of confirmed errors.

The disposition in quality_flags.csv describes the automatic action. Actual human validation remains pending. Record a human review in a separate review log with date, ticker, evidence/source, conclusion, action and reviewer. Any correction must be implemented reproducibly with its justification; do not edit the frozen raw files. No suspicious observation in the acquired dataset has been automatically deleted or winsorised.

## Returns and risk-free proxy

For an asset with adjusted price P:

- Simple return: `P[t] / P[t-1] - 1`.
- Log return: `log(P[t] / P[t-1])`.
- Validation identity: `expm1(log_return) == simple_return` within numerical precision.

Use log returns for statistical work. Use simple returns for portfolio value, compounding and rebalancing in the next milestone. A weighted average of asset log returns is not the exact log return of a rebalanced portfolio. This module produces asset returns only.

DGS3MO is a yield, not a price series or directly observed total-return investment. For a price interval from s to t, take the most recent numeric rate observation strictly before s. Require its age at s to be at most seven calendar days. Missing observations remain missing in raw data; the backward as-of match is permitted only for yields, not ETF prices.

Approximate cash accrual is `(annual_yield_percent / 100) * calendar_days(s, t) / 365`; its log equivalent is `log1p(accrual)`. Weekend accrual is included. This simple ACT/365 convention approximates a quoted investment-basis yield; it is not exact Treasury instrument pricing. The chosen quote date, age and interval length are exported so the approximation can be reviewed. The strict date lag avoids same-period/future quotes, but is not a guarantee about actual historical publication timestamps. FRED revisions and releases require vintage data for a fully point-in-time study.

## Stationarity and crisis coverage

ADF is run on each common-window asset log-return series with a constant and AIC lag selection at 5% significance. A unit-root rejection does not prove constant volatility, distributional stability or independence. ADF results on the complete coverage window are descriptive; model-specific training windows must be checked again. Short/constant series are reported as not estimable, not as a pass.

Date coverage is checked for calendar-year 2008, March 2020 and 2022. Having data for these dates does not mean stress tests or out-of-sample validation have been completed.

## Commands

From the repository root, after installing uv:

```bash
uv sync --locked
uv run --locked python run_data.py
uv run --locked pytest -q
```

The included frozen snapshot is the default; run_data.py itself makes no network requests in this mode. Dependency installation may need network access on a fresh computer. With dependencies already installed, verify offline reproduction with:

```bash
uv run --offline --locked python run_data.py
```

Explicitly acquire new data (internet required):

```bash
uv run --locked python run_data.py --download --start 2004-01-01 --end 2026-10-23
```

Select a historical snapshot without refreshing:

```bash
uv run --locked python run_data.py --snapshot SNAPSHOT_DIRECTORY_NAME
```

Outputs are under `output/data/<snapshot-id>/`: adjusted_prices.csv, simple_returns.csv, log_returns.csv, risk_free_returns.csv, coverage.csv, quality_flags.csv, stationarity.csv, summary.json, status.json and quality_report.md. Failed acquisition or preparation exits nonzero. Review warnings do not pretend to be human sign-off.

## Code map

- `src/domain/config.py`: validated, serialisable assumptions.
- `src/data/providers.py`: Yahoo/FRED acquisition contracts and adapters.
- `src/data/snapshots.py`: immutable acquisition storage, provenance and integrity checks.
- `src/data/preparation.py`: calendar, quality screening, returns and lagged rate alignment.
- `src/data/diagnostics.py`: descriptive ADF results.
- `src/application/data_pipeline.py`: preparation orchestration and output publication.
- `run_data.py`: CLI composition and explicit online/offline modes.
- `tests/test_data_foundation.py`: network-free financial examples and failure cases.
