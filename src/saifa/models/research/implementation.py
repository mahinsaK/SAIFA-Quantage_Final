"""Explicit cost assumptions, lagged-volume proxies and ex-date income evidence."""

from dataclasses import replace

import numpy as np
import pandas as pd

from saifa.domain.portfolio import PortfolioRun
from saifa.models.portfolio import performance_metrics


def fee_overlay(run: PortfolioRun, capital: float, annual_fee_bps: float) -> PortfolioRun:
    """Additional proportional admin charge; ETF expenses are already embedded in prices."""
    if not np.isfinite(annual_fee_bps) or not 0 <= annual_fee_bps < 10000:
        raise ValueError("Invalid additional annual fee")
    frame, trades = run.daily.copy(), run.transactions.copy()
    years = (frame.index - frame.index[0]).days.to_numpy() / 365.25
    scale = np.exp(-annual_fee_bps / 10000 * years)
    previous = np.r_[1.0, scale[:-1]]
    frame["additional_fee"] = frame.pre_trade_nav.to_numpy() * (previous - scale)
    for col in (
        "nav",
        "pre_trade_nav",
        "gross_traded",
        "transaction_cost",
        *[c for c in frame if c.endswith("_value")],
    ):
        frame[col] *= scale
    frame["daily_return"] = frame.nav.to_numpy() / np.r_[capital, frame.nav.to_numpy()[:-1]] - 1
    frame["cumulative_return"] = frame.nav / capital - 1
    frame["drawdown"] = (
        frame.nav / np.maximum.accumulate(np.r_[capital, frame.nav.to_numpy()])[1:] - 1
    )
    trade_scale = np.exp(
        -annual_fee_bps / 10000 * (trades.index - frame.index[0]).days.to_numpy() / 365.25
    )
    for col in (
        "nav_before",
        "nav_after",
        "gross_traded",
        "transaction_cost",
        *[c for c in trades if c.endswith("_trade")],
    ):
        trades[col] *= trade_scale
    return replace(run, daily=frame, transactions=trades)


def liquidity_proxy(transactions: pd.DataFrame, raw: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for ticker, frame in raw.items():
        notional = frame.Close * frame.Volume
        adv = (
            notional.where(np.isfinite(notional) & (frame.Volume >= 0))
            .rolling(20, min_periods=20)
            .mean()
            .shift(1)
        )
        for date, trade in transactions.iterrows():
            amount = abs(float(trade.get(f"{ticker}_trade", 0)))
            if amount <= 1e-7:
                continue
            volume = adv.get(date, np.nan)
            available = np.isfinite(volume) and volume > 0
            rows.append(
                {
                    "Date": str(date.date()),
                    "strategy": trade.strategy,
                    "ticker": ticker,
                    "gross_asset_trade_usd": amount,
                    "lagged_20_session_dollar_volume": volume,
                    "participation_proxy": amount / volume if available else np.nan,
                    "status": "proxy_requires_review" if available else "unavailable",
                    "reason": "Historical daily-volume proxy; split-adjusted units and actual intraday liquidity need review. Not an impact or spread estimate.",
                }
            )
    return pd.DataFrame(rows)


def income_proxy(
    raw: dict[str, pd.DataFrame], portfolios: pd.DataFrame, start: str, end: str, capital: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Constant-notional ex-date distribution proxy, deliberately separate from total returns."""
    summaries, ledger = [], []
    for strategy, weights in portfolios.iterrows():
        total = 0.0
        covered_weight = 0.0
        covered_assets = []
        reasons = []
        for ticker, weight in weights.items():
            if weight <= 1e-10:
                continue
            frame = raw[ticker]
            sample = frame.loc[
                (frame.index > pd.Timestamp(start)) & (frame.index <= pd.Timestamp(end))
            ]
            if not {"Dividends", "Capital Gains", "Stock Splits", "Close"}.issubset(sample):
                reasons.append(f"{ticker}: missing distribution fields")
                continue
            if sample["Stock Splits"].ne(0).any():
                reasons.append(
                    f"{ticker}: split/distribution unit convention needs independent review"
                )
                continue
            prior = frame.Close.shift(1).reindex(sample.index)
            distributions = sample.Dividends + sample["Capital Gains"]
            if (
                not np.isfinite(distributions).all()
                or (distributions < 0).any()
                or not np.isfinite(prior).all()
                or (prior <= 0).any()
            ):
                reasons.append(f"{ticker}: invalid prior price or distribution")
                continue
            proxy = capital * weight * distributions / prior
            total += float(proxy.sum())
            covered_weight += float(weight)
            covered_assets.append(ticker)
            for date in sample.index[distributions > 0]:
                ledger.append(
                    {
                        "strategy": strategy,
                        "ex_date": str(date.date()),
                        "ticker": ticker,
                        "distribution_per_share": distributions.loc[date],
                        "prior_close": prior.loc[date],
                        "fixed_notional_distribution_proxy_usd": proxy.loc[date],
                        "basis": "Constant target exposure, ex-date recognition; no actual payment-date or tax data",
                    }
                )
        summaries.append(
            {
                "strategy": strategy,
                "start_date": start,
                "end_date": end,
                "reference_nav": capital,
                "distribution_proxy_usd": total if not reasons else np.nan,
                "partial_eligible_proxy_usd": total if covered_assets else np.nan,
                "covered_target_weight": covered_weight,
                "covered_assets": ", ".join(covered_assets),
                "status": "proxy_only" if not reasons else "unavailable",
                "reason": "; ".join(reasons)
                if reasons
                else "Not actual fund cash: constant exposure, vendor ex-dates, no payment dates or withholding. Never add this to adjusted-price returns.",
            }
        )
    return pd.DataFrame(summaries), pd.DataFrame(ledger)


def cost_metrics(run: PortfolioRun, capital: float, annual_days: int, fee_bps: float) -> dict:
    charged = fee_overlay(run, capital, fee_bps)
    return {
        **performance_metrics(charged, capital, annual_days),
        "additional_annual_fee_bps": fee_bps,
        "total_additional_fees": float(charged.daily.additional_fee.sum()),
    }
