"""Conditional ten-year spending simulations from joint monthly return/CPI blocks."""

import numpy as np
import pandas as pd
from scipy.stats import norm

from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.domain.research import ResearchConfig
from saifa.models.research.robustness import block_indices


def joint_monthly_inputs(month_end_prices: pd.DataFrame, cpi: pd.Series) -> pd.DataFrame:
    prices = month_end_prices.copy()
    prices.index = prices.index.to_period("M")
    if prices.index.has_duplicates or not prices.index.is_monotonic_increasing:
        raise ValueError("Unique ordered monthly prices required")
    inflation = cpi.copy()
    inflation.index = inflation.index.to_period("M")
    if inflation.index.has_duplicates or not inflation.index.is_monotonic_increasing:
        raise ValueError("Unique ordered CPI months required")
    # Keep calendar slots while differencing. Missing CPI invalidates both adjacent ratios.
    inflation = inflation.reindex(
        pd.period_range(inflation.index[0], inflation.index[-1], freq="M")
    )
    returns = prices.reindex(
        pd.period_range(prices.index[0], prices.index[-1], freq="M")
    ).pct_change(fill_method=None)
    joint = returns.join(
        inflation.pct_change(fill_method=None).rename("inflation"), how="inner"
    ).dropna()
    if len(joint) < 24 or not np.isfinite(joint.to_numpy()).all() or (joint <= -1).any().any():
        raise ValueError("At least 24 finite complete monthly return/inflation rows required")
    joint.index.name = "month"
    return joint


def monthly_factors(
    sampled_returns: np.ndarray, weights: np.ndarray, cost: float
) -> tuple[np.ndarray, np.ndarray]:
    if (
        sampled_returns.ndim != 3
        or sampled_returns.shape[2] != len(weights)
        or not np.isfinite(sampled_returns).all()
        or (sampled_returns < -1).any()
        or not np.isclose(weights.sum(), 1)
        or (weights < 0).any()
        or not 0 <= cost < 1
    ):
        raise ValueError("Invalid monthly simulation inputs")
    values = (1 + sampled_returns) * weights
    pre = values.sum(axis=2)
    if cost == 0:
        return pre, np.zeros_like(pre)
    low, high = pre * (1 - cost) / (1 + cost), pre.copy()
    for _ in range(52):
        mid = (low + high) / 2
        equation = mid + cost * np.abs(mid[:, :, None] * weights - values).sum(axis=2) - pre
        high = np.where(equation > 0, mid, high)
        low = np.where(equation <= 0, mid, low)
    after = (low + high) / 2
    fees = cost * np.abs(after[:, :, None] * weights - values).sum(axis=2)
    if not np.allclose(after + fees, pre, atol=1e-12, rtol=1e-12):
        raise RuntimeError("Monthly rebalance is not self-financing")
    return after, fees


def wilson_interval(successes: int, observations: int) -> tuple[float, float]:
    if observations < 1 or not 0 <= successes <= observations:
        raise ValueError("Invalid simulation event counts")
    z = norm.ppf(0.975)
    p = successes / observations
    denominator = 1 + z * z / observations
    center = (p + z * z / (2 * observations)) / denominator
    half = z * np.sqrt(p * (1 - p) / observations + z * z / (4 * observations**2)) / denominator
    low = 0.0 if successes == 0 else max(0.0, center - half)
    high = 1.0 if successes == observations else min(1.0, center + half)
    return low, high


def simulate_cashflows(
    factors: np.ndarray,
    rebalance_fees: np.ndarray,
    inflation: np.ndarray,
    capital: float,
    cost: float,
    withdrawal_rate: float,
) -> tuple[dict, np.ndarray]:
    if (
        factors.shape != inflation.shape
        or rebalance_fees.shape != factors.shape
        or factors.ndim != 2
        or min(factors.shape) < 1
        or not np.isfinite(factors).all()
        or not np.isfinite(rebalance_fees).all()
        or (rebalance_fees < 0).any()
        or not np.isfinite(inflation).all()
        or (factors < 0).any()
        or (inflation <= -1).any()
        or not np.isfinite(capital)
        or capital <= 0
        or not 0 <= cost < 1
        or not 0 <= withdrawal_rate < 1
    ):
        raise ValueError("Invalid cash-flow simulation inputs")
    paths, months = factors.shape
    nav = np.full(paths, capital / (1 + cost))
    deflator = np.ones(paths)
    total_paid = np.zeros(paths)
    total_fees = np.full(paths, capital - capital / (1 + cost))
    shortfall = np.zeros(paths, dtype=bool)
    real_paths = [nav.copy()]
    first_payment_deflator = None
    for t in range(months):
        total_fees += nav * rebalance_fees[:, t]
        pre = nav * factors[:, t]
        deflator *= 1 + inflation[:, t]
        paid = np.zeros(paths)
        sale_fee = np.zeros(paths)
        if (t + 1) % 12 == 0:
            if first_payment_deflator is None:
                first_payment_deflator = deflator.copy()
            requested = capital * withdrawal_rate * deflator / first_payment_deflator
            paid = np.minimum(requested, pre * (1 - cost))
            shortfall |= paid < requested - 1e-7
            sale_fee = paid * cost / (1 - cost)
        nav = np.maximum(0, pre - paid - sale_fee)
        if not np.allclose(pre, nav + paid + sale_fee, atol=1e-7, rtol=1e-12):
            raise RuntimeError("Simulated withdrawal is not funded")
        total_paid += paid
        total_fees += sale_fee
        real_paths.append(nav / deflator)
    real = nav / deflator
    successes = int((~shortfall).sum())
    low, high = wilson_interval(successes, paths)
    result = {
        "paths": paths,
        "months": months,
        "withdrawal_rate": withdrawal_rate,
        "no_shortfall_fraction": successes / paths,
        "conditional_wilson_low": low,
        "conditional_wilson_high": high,
        "ending_real_p05": float(np.quantile(real, 0.05)),
        "ending_real_median": float(np.median(real)),
        "ending_real_p95": float(np.quantile(real, 0.95)),
        "preserved_real_capital_fraction": float(np.mean(real >= capital)),
        "after_spending_3pct_growth_fraction": float(
            np.mean(real >= capital * 1.03 ** (months / 12))
        ),
        "mean_nominal_paid": float(total_paid.mean()),
        "mean_total_costs": float(total_fees.mean()),
    }
    return result, np.asarray(real_paths).T


def spending_experiment(
    joint: pd.DataFrame,
    portfolios: pd.DataFrame,
    policy: OptimisationConfig,
    settings: ResearchConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    # Calendar gaps must restart a block; never bridge the missing CPI ratios.
    consecutive = np.r_[np.diff(joint.index.asi8) == 1, False]
    indices = block_indices(
        len(joint),
        settings.spending_months,
        settings.spending_paths,
        settings.spending_block,
        settings.seed,
        consecutive,
    )
    sampled_returns = joint.loc[:, list(UNIVERSE)].to_numpy()[indices]
    sampled_inflation = joint.inflation.to_numpy()[indices]
    records, fans = [], []
    for strategy, row in portfolios.iterrows():
        weights = row.reindex(UNIVERSE).to_numpy(dtype=float)
        factors, fees = monthly_factors(sampled_returns, weights, policy.transaction_cost_rate)
        for spread in (0.0, 0.02):
            inflation = (1 + sampled_inflation) * (1 + spread) ** (1 / 12) - 1
            for rate in (0.02, 0.03, 0.04):
                result, paths = simulate_cashflows(
                    factors,
                    fees,
                    inflation,
                    policy.initial_capital,
                    policy.transaction_cost_rate,
                    rate,
                )
                records.append({"strategy": strategy, "inflation_annual_spread": spread, **result})
                q = np.quantile(paths, [0.05, 0.5, 0.95], axis=0)
                fans.extend(
                    {
                        "strategy": strategy,
                        "withdrawal_rate": rate,
                        "inflation_annual_spread": spread,
                        "month": t,
                        "real_p05": q[0, t],
                        "real_median": q[1, t],
                        "real_p95": q[2, t],
                    }
                    for t in range(paths.shape[1])
                )
    return pd.DataFrame(records), pd.DataFrame(fans)
