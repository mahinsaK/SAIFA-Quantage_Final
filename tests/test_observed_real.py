"""Frozen CPI integrity and hand-checkable observed purchasing-power arithmetic."""

import json
from hashlib import sha256

import pandas as pd
import pytest

from saifa.data.inflation import load_frozen_cpi
from saifa.models.observed_real import observed_real_growth


def cpi_fixture(tmp_path):
    folder = tmp_path / "data/inflation"
    folder.mkdir(parents=True)
    source = folder / "CPIAUCSL.csv"
    source.write_text(
        "observation_date,CPIAUCSL\n2022-01-01,100\n2022-02-01,101\n2022-03-01,\n2022-04-01,103\n"
    )
    manifest = {
        "schema_version": 1,
        "status": "complete",
        "series": "CPIAUCSL",
        "file": "CPIAUCSL.csv",
        "file_sha256": sha256(source.read_bytes()).hexdigest(),
        "portfolio_as_of_date": "2022-05-15",
        "latest_observation_release_date": "2022-05-11",
        "first_observation": "2022-01-01",
        "last_observation": "2022-04-01",
        "observations": 4,
        "missing_observations": ["2022-03-01"],
    }
    (folder / "manifest.json").write_text(json.dumps(manifest))
    return source, manifest


def test_frozen_cpi_accepts_declared_missing_interior_but_not_tampering(tmp_path):
    source, _ = cpi_fixture(tmp_path)
    cpi, _ = load_frozen_cpi(tmp_path, "2022-05-15")
    assert pd.isna(cpi.loc["2022-03-01"])
    assert cpi.loc["2022-04-01"] == 103
    source.write_text(source.read_text().replace("2022-04-01,103", "2022-04-01,999"))
    with pytest.raises(ValueError, match="checksum"):
        load_frozen_cpi(tmp_path, "2022-05-15")


def test_frozen_cpi_rejects_unreleased_or_undeclared_missing_data(tmp_path):
    _, manifest = cpi_fixture(tmp_path)
    manifest["latest_observation_release_date"] = "2022-05-16"
    path = tmp_path / "data/inflation/manifest.json"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="as-of"):
        load_frozen_cpi(tmp_path, "2022-05-15")
    manifest["latest_observation_release_date"] = "2022-05-11"
    manifest["missing_observations"] = []
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="missing"):
        load_frozen_cpi(tmp_path, "2022-05-15")


def test_observed_real_growth_uses_costed_nav_and_last_cpi_month_only():
    daily = pd.DataFrame(
        {"nav": [990, 1100, 1200]},
        index=["2022-01-03", "2023-01-31", "2023-02-01"],
    )
    cpi = pd.Series([100, 110], index=pd.to_datetime(["2022-01-01", "2023-01-01"]))
    result = observed_real_growth("test", daily, cpi, 1000, 0.03, "2023-02-15")
    assert result.end_date == "2023-01-31"
    assert result.ending_nominal_wealth == 1100
    assert result.cpi_deflator == pytest.approx(1.1)
    assert result.ending_real_wealth == pytest.approx(1000)
    assert result.annualised_real_growth == pytest.approx(0)
    assert not result.objective_met_in_observed_period
    # The later February NAV cannot enter a comparison ending with January CPI.
    daily.loc["2023-02-01", "nav"] = 1_000_000
    assert observed_real_growth("test", daily, cpi, 1000, 0.03, "2023-02-15") == result


def test_observed_real_growth_withholds_missing_endpoint_cpi():
    daily = pd.DataFrame({"nav": [1000, 1100]}, index=["2022-01-03", "2023-01-31"])
    cpi = pd.Series([100, float("nan")], index=pd.to_datetime(["2022-01-01", "2023-01-01"]))
    with pytest.raises(ValueError, match="CPI"):
        observed_real_growth("test", daily, cpi, 1000, 0.03, "2023-02-15")
