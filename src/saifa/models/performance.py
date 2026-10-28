"""Institutional performance ratios and CAPM diagnostics."""

import numpy as np
import pandas as pd


def performance_ratios(
    portfolio_returns: pd.Series,
    market_returns: pd.Series,
    risk_free_returns: pd.Series,
    benchmark_returns: pd.Series,
    annual_trading_days: int = 252,
) -> dict[str, float]:
    frame = pd.concat(
        {
            "portfolio": portfolio_returns,
            "market": market_returns,
            "risk_free": risk_free_returns,
            "benchmark": benchmark_returns,
        },
        axis=1,
        join="inner",
    ).dropna()
    if len(frame) < 3 or not np.isfinite(frame.to_numpy()).all():
        raise ValueError("Performance ratios need at least three aligned finite observations")
    excess = frame.portfolio - frame.risk_free
    market_excess = frame.market - frame.risk_free
    benchmark_excess = frame.portfolio - frame.benchmark
    annual_return = float(frame.portfolio.mean() * annual_trading_days)
    annual_risk_free = float(frame.risk_free.mean() * annual_trading_days)
    volatility = float(frame.portfolio.std(ddof=1) * np.sqrt(annual_trading_days))
    downside = np.minimum(excess.to_numpy(), 0.0)
    downside_deviation = float(np.sqrt(np.mean(downside**2)) * np.sqrt(annual_trading_days))
    market_variance = float(market_excess.var(ddof=1))
    beta = (
        float(np.cov(excess, market_excess, ddof=1)[0, 1] / market_variance)
        if market_variance > 0
        else np.nan
    )
    alpha_daily = (
        float(excess.mean() - beta * market_excess.mean()) if np.isfinite(beta) else np.nan
    )
    active_risk = float(benchmark_excess.std(ddof=1) * np.sqrt(annual_trading_days))
    wealth = (1 + frame.portfolio).cumprod()
    maximum_drawdown = float((wealth / wealth.cummax() - 1).min())
    geometric_return = float(wealth.iloc[-1] ** (annual_trading_days / len(frame)) - 1)
    return {
        "observations": float(len(frame)),
        "annualised_arithmetic_return": annual_return,
        "annualised_risk_free": annual_risk_free,
        "annualised_volatility": volatility,
        "sharpe_ratio": (annual_return - annual_risk_free) / volatility
        if volatility > 0
        else np.nan,
        "sortino_ratio": (annual_return - annual_risk_free) / downside_deviation
        if downside_deviation > 0
        else np.nan,
        "beta": beta,
        "treynor_ratio": (annual_return - annual_risk_free) / beta
        if np.isfinite(beta) and abs(beta) > 1e-12
        else np.nan,
        "jensen_alpha": alpha_daily * annual_trading_days,
        "information_ratio": float(benchmark_excess.mean() * annual_trading_days / active_risk)
        if active_risk > 0
        else np.nan,
        "maximum_drawdown": maximum_drawdown,
        "calmar_ratio": geometric_return / abs(maximum_drawdown)
        if maximum_drawdown < 0
        else np.nan,
    }
