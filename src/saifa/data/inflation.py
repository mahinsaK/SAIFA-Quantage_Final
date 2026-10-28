"""Load the frozen FRED CPI overlay independently of the original market snapshot."""

import json
from pathlib import Path

import numpy as np
import pandas as pd

from saifa.data.snapshots import file_hash


def load_frozen_cpi(root: Path, as_of: str) -> tuple[pd.Series, dict]:
    folder = root / "data/inflation"
    manifest = json.loads((folder / "manifest.json").read_text())
    if (
        manifest.get("schema_version") != 1
        or manifest.get("status") != "complete"
        or manifest.get("series") != "CPIAUCSL"
        or manifest.get("file") != "CPIAUCSL.csv"
        or manifest.get("portfolio_as_of_date") != as_of
        or pd.Timestamp(manifest["latest_observation_release_date"]) > pd.Timestamp(as_of)
    ):
        raise ValueError("Frozen CPI metadata is incomplete or unavailable at the portfolio as-of")
    path = folder / "CPIAUCSL.csv"
    if file_hash(path) != manifest["file_sha256"]:
        raise ValueError("Frozen CPI file differs from its recorded checksum")
    frame = pd.read_csv(path)
    if frame.columns.tolist() != ["observation_date", "CPIAUCSL"]:
        raise ValueError("Frozen CPI columns differ from the documented source")
    if frame.empty:
        raise ValueError("Frozen CPI contains no monthly observations")
    dates = pd.DatetimeIndex(pd.to_datetime(frame.observation_date, errors="raise"))
    values = pd.to_numeric(frame.CPIAUCSL, errors="raise").to_numpy(dtype=float)
    expected = pd.date_range(dates[0], dates[-1], freq="MS")
    missing = dates[np.isnan(values)].strftime("%Y-%m-%d").tolist()
    if (
        len(dates) != manifest["observations"]
        or not dates.equals(expected)
        or str(dates[0].date()) != manifest["first_observation"]
        or str(dates[-1].date()) != manifest["last_observation"]
        or dates[-1] > pd.Timestamp(as_of)
        or missing != manifest.get("missing_observations", [])
        or not np.isfinite(values[~np.isnan(values)]).all()
        or np.any(values[~np.isnan(values)] <= 0)
        or np.isnan(values[0])
        or np.isnan(values[-1])
    ):
        raise ValueError("Frozen CPI has missing, duplicate, future or invalid monthly values")
    return pd.Series(values, index=dates, name="CPIAUCSL"), manifest
