"""Small, hand-checkable cases and failure modes; no live network required."""

import json

import numpy as np
import pandas as pd
import pytest

from src.application.data_pipeline import build_data
from src.data.diagnostics import stationarity_table
from src.data.preparation import align_risk_free, audit_prices, calculate_returns, trading_sessions
from src.data.providers import YahooPrices, parse_fred
from src.data.snapshots import acquire, load_snapshot, resolve_snapshot
from src.domain.config import DataConfig


def frame(values, dates):
    return pd.DataFrame({"Adj Close": values, "Close": values}, index=dates)


def test_returns_use_adjusted_prices_and_compound_correctly():
    dates = pd.bdate_range("2024-01-02", periods=3)
    prices = frame([100, 110, 99], dates)
    prices["Close"] = [100, 55, 49.5]  # Illustrative split-adjusted distinction.
    config = DataConfig(
        start="2024-01-02", end_exclusive="2024-01-05", tickers=("SPY",), minimum_prices=2
    )
    audited = audit_prices({"SPY": prices}, config, dates)
    simple, log = calculate_returns(audited.prices)
    np.testing.assert_allclose(simple.SPY, [0.10, -0.10])
    np.testing.assert_allclose(np.expm1(log.SPY), simple.SPY)
    assert (1 + simple.SPY).prod() - 1 == pytest.approx(-0.01)
    assert np.expm1(log.SPY.sum()) == pytest.approx(-0.01)


def test_missing_session_is_blocked_not_filled_or_bridged():
    dates = pd.bdate_range("2024-01-02", periods=4)
    prices = frame([100, 110, 120], dates.delete(1))
    config = DataConfig(tickers=("SPY",), minimum_prices=2)
    audited = audit_prices({"SPY": prices}, config, dates)
    assert audited.prices.loc[dates[1]].isna().all()
    assert "missing_session_price" in audited.flags.kind.values
    with pytest.raises(ValueError, match="refusing to fill"):
        calculate_returns(audited.prices)


def test_leading_unavailable_history_uses_common_start_only():
    dates = pd.bdate_range("2024-01-02", periods=4)
    frames = {"SPY": frame([100, 101, 102, 103], dates), "GLD": frame([50, 51, 52], dates[1:])}
    audited = audit_prices(frames, DataConfig(tickers=("SPY", "GLD"), minimum_prices=2), dates)
    assert audited.prices.index[0] == dates[1]
    assert audited.coverage.set_index("ticker").loc["GLD", "leading_sessions_without_data"] == 1
    assert not (audited.flags.severity == "error").any()


def test_large_real_loss_retained_and_flagged():
    dates = pd.bdate_range("2024-01-02", periods=3)
    audited = audit_prices(
        {"SPY": frame([100, 70, 80], dates)}, DataConfig(tickers=("SPY",), minimum_prices=2), dates
    )
    assert audited.prices.loc[dates[1], "SPY"] == 70
    assert "large_daily_return" in audited.flags.kind.values
    assert not (audited.flags.severity == "error").any()


@pytest.mark.parametrize("bad", [0, -5, np.inf])
def test_invalid_prices_block_returns(bad):
    dates = pd.bdate_range("2024-01-02", periods=3)
    audited = audit_prices(
        {"SPY": frame([100, bad, 101], dates)},
        DataConfig(tickers=("SPY",), minimum_prices=2),
        dates,
    )
    assert "invalid_adjusted_price" in audited.flags.kind.values
    with pytest.raises(ValueError, match="Invalid/missing"):
        calculate_returns(audited.prices)


def test_duplicate_quotes_fail_instead_of_silent_deduplication():
    dates = pd.DatetimeIndex(["2024-01-02", "2024-01-02", "2024-01-03"])
    with pytest.raises(ValueError, match="unique and ordered"):
        audit_prices(
            {"SPY": frame([100, 101, 102], dates)},
            DataConfig(tickers=("SPY",), minimum_prices=2),
            dates.unique(),
        )


def test_weekend_quote_is_flagged_as_unexpected_session():
    dates = pd.DatetimeIndex(["2024-01-05", "2024-01-06", "2024-01-08"])
    audited = audit_prices(
        {"SPY": frame([100, 101, 102], dates)},
        DataConfig(tickers=("SPY",), minimum_prices=2),
        dates[[0, 2]],
    )
    assert "unexpected_session" in audited.flags.kind.values


def test_flat_run_is_reported_without_removing_quotes():
    dates = pd.bdate_range("2024-01-02", periods=7)
    audited = audit_prices(
        {"SPY": frame([100] * 7, dates)}, DataConfig(tickers=("SPY",), minimum_prices=2), dates
    )
    assert "flat_price_run" in audited.flags.kind.values
    assert len(audited.prices) == 7


def test_calendar_excludes_us_holiday_and_weekend():
    config = DataConfig(start="2024-07-03", end_exclusive="2024-07-09")
    sessions = trading_sessions(config)
    assert list(sessions.strftime("%Y-%m-%d")) == ["2024-07-03", "2024-07-05", "2024-07-08"]


def test_calendar_accepts_non_session_request_boundaries():
    config = DataConfig(start="2004-01-01", end_exclusive="2004-01-05")
    assert list(trading_sessions(config).strftime("%Y-%m-%d")) == ["2004-01-02"]


def test_risk_free_uses_only_quote_before_period_start_and_calendar_days():
    rates = pd.Series(
        [5.0, 99.0, 80.0], index=pd.to_datetime(["2024-01-04", "2024-01-05", "2024-01-08"])
    )
    dates = pd.to_datetime(["2024-01-05", "2024-01-08"])
    output = align_risk_free(rates, dates, 7)
    assert output.iloc[0].annual_yield_percent == 5.0
    assert output.iloc[0].simple_return == pytest.approx(0.05 * 3 / 365)
    assert output.iloc[0].observation_date < output.iloc[0].period_start
    changed = rates.copy()
    changed.iloc[1:] = -20
    pd.testing.assert_frame_equal(output, align_risk_free(changed, dates, 7))


@pytest.mark.parametrize("quote_date", ["2023-12-01", "2024-01-08"])
def test_stale_or_future_only_rates_fail(quote_date):
    rates = pd.Series([5.0], index=pd.to_datetime([quote_date]))
    with pytest.raises(ValueError, match="Missing/stale"):
        align_risk_free(rates, pd.to_datetime(["2024-01-05", "2024-01-08"]), 7)


def test_fred_preserves_missing_and_percentage_units():
    result = parse_fred("observation_date,DGS3MO\n2024-01-01,.\n2024-01-02,5.2\n", "DGS3MO")
    assert np.isnan(result.iloc[0])
    assert result.iloc[1] == 5.2
    with pytest.raises(ValueError):
        parse_fred("date,DGS3MO\n2024-01-02,error\n", "DGS3MO")


def test_adf_constant_series_is_not_a_spurious_pass():
    result = stationarity_table(pd.DataFrame({"SPY": [0.0] * 150}))
    assert result.iloc[0].status == "not_estimable"


class FakePrices:
    def fetch(self, ticker, start, end):
        dates = pd.to_datetime(["2024-01-02", "2024-01-03", "2024-01-04"])
        return frame([100, 101, 102], dates)


class FakeRates:
    def fetch_csv(self, series, start, end):
        return "observation_date,DGS3MO\n2023-12-29,5.0\n2024-01-02,5.1\n2024-01-03,5.2\n"


def small_config():
    return DataConfig(
        start="2024-01-02", end_exclusive="2024-01-05", tickers=("SPY",), minimum_prices=2
    )


def test_snapshot_roundtrip_offline_reproduction_and_tampering(tmp_path):
    snapshot = acquire(tmp_path, small_config(), FakePrices(), FakeRates())
    assert resolve_snapshot(tmp_path) == snapshot
    config, _, frames, _ = load_snapshot(snapshot)
    assert config == small_config()
    assert len(frames["SPY"]) == 3
    first_output = build_data(tmp_path, snapshot)
    first_summary = (first_output / "summary.json").read_bytes()
    second_output = build_data(tmp_path, snapshot)
    assert (second_output / "summary.json").read_bytes() == first_summary
    assert json.loads((second_output / "status.json").read_text())["status"] == "complete"
    with (snapshot / "SPY.csv").open("a") as handle:
        handle.write("corruption\n")
    with pytest.raises(ValueError, match="integrity"):
        load_snapshot(snapshot)


def test_failed_acquisition_does_not_replace_latest(tmp_path):
    good = acquire(tmp_path, small_config(), FakePrices(), FakeRates())

    class BrokenPrices:
        def fetch(self, *args):
            raise RuntimeError("provider unavailable")

    with pytest.raises(RuntimeError, match="unavailable"):
        acquire(tmp_path, small_config(), BrokenPrices(), FakeRates())
    assert resolve_snapshot(tmp_path) == good
    incomplete = next(p for p in good.parent.iterdir() if p != good)
    with pytest.raises(ValueError, match="incomplete"):
        load_snapshot(incomplete)


def test_yahoo_settings_are_explicit_and_raw_close_is_not_a_fallback(monkeypatch, tmp_path):
    class FakeTicker:
        def history(self, **kwargs):
            assert kwargs["auto_adjust"] is False
            assert kwargs["repair"] is False
            assert kwargs["keepna"] is True
            return pd.DataFrame({"Close": [100]}, index=pd.to_datetime(["2024-01-02"]))

    monkeypatch.setattr("src.data.providers.yf.Ticker", lambda ticker: FakeTicker())
    with pytest.raises(ValueError, match="Adj Close"):
        YahooPrices(tmp_path).fetch("SPY", "2024-01-01", "2024-01-03")


def test_blocking_quality_error_publishes_failure_and_audit(tmp_path):
    class MissingQuotePrices:
        def fetch(self, *args):
            return frame([100, 102], pd.to_datetime(["2024-01-02", "2024-01-04"]))

    snapshot = acquire(tmp_path, small_config(), MissingQuotePrices(), FakeRates())
    with pytest.raises(ValueError, match="blocking data flags"):
        build_data(tmp_path, snapshot)
    output = tmp_path / "output/data" / snapshot.name
    assert json.loads((output / "status.json").read_text())["status"] == "failed"
    assert "missing_session_price" in pd.read_csv(output / "quality_flags.csv").kind.values
    assert not (output / "simple_returns.csv").exists()
