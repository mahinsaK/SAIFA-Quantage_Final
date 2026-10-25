"""Constrained mean-variance portfolio construction."""

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.domain.portfolio import AllocationFit, OptimisationResult

EQUITIES = ("SPY", "EFA", "EEM", "XLE", "XLK")
SECTORS = ("XLE", "XLK")


def fit_target_allocations(
    asset_returns: pd.DataFrame, risk_free_returns: pd.Series, config: OptimisationConfig
) -> AllocationFit:
    """Fit frozen candidates from development rows only, without evaluation data."""
    development = asset_returns.loc[asset_returns.index < config.development_end_exclusive]
    means, covariance = annualised_inputs(development, config.annual_trading_days)
    if not risk_free_returns.index.is_unique:
        raise ValueError("Development risk-free dates must be unique")
    rates = risk_free_returns.reindex(development.index)
    if not np.isfinite(rates.to_numpy(dtype=float)).all():
        raise ValueError("Finite risk-free returns are required on all development dates")
    annual_risk_free = float(rates.mean() * config.annual_trading_days)
    candidates = tuple(
        optimise_portfolio(name, means, covariance, annual_risk_free, config)
        for name in ("minimum_volatility", "maximum_sharpe")
    )
    if not all(result.success for result in candidates):
        messages = "; ".join(f"{r.name}: {r.message}" for r in candidates)
        raise RuntimeError(f"Portfolio optimisation failed: {messages}")
    return AllocationFit(means, covariance, annual_risk_free, candidates)


def annualised_inputs(
    simple_returns: pd.DataFrame, annual_trading_days: int
) -> tuple[pd.Series, pd.DataFrame]:
    """Estimate arithmetic annual returns and covariance from development data."""
    if tuple(simple_returns.columns) != UNIVERSE:
        raise ValueError("Returns must contain the eligible universe in prescribed order")
    if len(simple_returns) < annual_trading_days or simple_returns.isna().any().any():
        raise ValueError("At least one complete year of finite returns is required")
    values = simple_returns.to_numpy(dtype=float)
    if not np.isfinite(values).all():
        raise ValueError("Returns must be finite")
    means = simple_returns.mean() * annual_trading_days
    covariance = simple_returns.cov() * annual_trading_days
    if np.linalg.eigvalsh(covariance.to_numpy()).min() < -1e-10:
        raise ValueError("Estimated covariance matrix is not positive semidefinite")
    return means, covariance


def policy_constraints(config: OptimisationConfig) -> list[dict]:
    index = {ticker: position for position, ticker in enumerate(UNIVERSE)}
    return [
        {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
        {"type": "ineq", "fun": lambda w: w[index["AGG"]] - config.bond_minimum},
        {
            "type": "ineq",
            "fun": lambda w: config.equity_maximum - sum(w[index[ticker]] for ticker in EQUITIES),
        },
        {
            "type": "ineq",
            "fun": lambda w: (
                config.sectors_combined_maximum - sum(w[index[ticker]] for ticker in SECTORS)
            ),
        },
    ]


def validate_policy_weights(weights: pd.Series, config: OptimisationConfig) -> None:
    if tuple(weights.index) != UNIVERSE:
        raise ValueError("Weights must use the prescribed universe order")
    tolerance = 1e-7
    if not np.isfinite(weights.to_numpy()).all() or abs(weights.sum() - 1) > tolerance:
        raise ValueError("Weights must be finite and sum to one")
    if (weights < -tolerance).any() or (weights > config.single_asset_maximum + tolerance).any():
        raise ValueError("Long-only or single-asset limit violated")
    if weights["AGG"] < config.bond_minimum - tolerance:
        raise ValueError("AGG minimum violated")
    if weights[list(EQUITIES)].sum() > config.equity_maximum + tolerance:
        raise ValueError("Total-equity limit violated")
    if weights[list(SECTORS)].sum() > config.sectors_combined_maximum + tolerance:
        raise ValueError("Combined-sector limit violated")
    if (weights[list(SECTORS)] > config.sector_maximum + tolerance).any():
        raise ValueError("Individual-sector limit violated")
    if weights["GLD"] > config.gold_maximum + tolerance:
        raise ValueError("Gold limit violated")


def _bounds(config: OptimisationConfig) -> tuple[tuple[float, float], ...]:
    maxima = {
        "GLD": config.gold_maximum,
        "XLE": config.sector_maximum,
        "XLK": config.sector_maximum,
    }
    return tuple((0.0, maxima.get(ticker, config.single_asset_maximum)) for ticker in UNIVERSE)


def _portfolio_statistics(
    weights: np.ndarray, means: np.ndarray, covariance: np.ndarray, risk_free_rate: float
) -> tuple[float, float, float]:
    expected = float(weights @ means)
    volatility = float(np.sqrt(max(weights @ covariance @ weights, 0.0)))
    sharpe = (expected - risk_free_rate) / volatility if volatility > 0 else np.nan
    return expected, volatility, sharpe


def optimise_portfolio(
    name: str,
    means: pd.Series,
    covariance: pd.DataFrame,
    risk_free_rate: float,
    config: OptimisationConfig,
    target_return: float | None = None,
) -> OptimisationResult:
    """Solve minimum variance, maximum Sharpe, or target-return minimum variance."""
    mean_values = means.reindex(UNIVERSE).to_numpy(dtype=float)
    covariance_values = covariance.reindex(index=UNIVERSE, columns=UNIVERSE).to_numpy(dtype=float)
    constraints = policy_constraints(config)
    if target_return is not None:
        constraints = [
            *constraints,
            {"type": "eq", "fun": lambda w: float(w @ mean_values - target_return)},
        ]
    initial = np.array([0.2, 0.0, 0.0, 0.6, 0.2, 0.0, 0.0])

    def variance(w: np.ndarray) -> float:
        return float(w @ covariance_values @ w)

    def negative_sharpe(w: np.ndarray) -> float:
        expected, volatility, _ = _portfolio_statistics(
            w, mean_values, covariance_values, risk_free_rate
        )
        return -(expected - risk_free_rate) / max(volatility, 1e-12)

    objective = negative_sharpe if name == "maximum_sharpe" else variance
    solution = minimize(
        objective,
        initial,
        method="SLSQP",
        bounds=_bounds(config),
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 2_000},
    )
    if not solution.success:
        return OptimisationResult(
            name,
            pd.Series(solution.x, index=UNIVERSE),
            np.nan,
            np.nan,
            np.nan,
            False,
            solution.message,
        )
    weights = pd.Series(solution.x, index=UNIVERSE, dtype=float)
    weights[weights.abs() < 1e-10] = 0.0
    validate_policy_weights(weights, config)
    expected, volatility, sharpe = _portfolio_statistics(
        weights.to_numpy(), mean_values, covariance_values, risk_free_rate
    )
    return OptimisationResult(name, weights, expected, volatility, sharpe, True, solution.message)


def efficient_frontier(
    means: pd.Series,
    covariance: pd.DataFrame,
    risk_free_rate: float,
    config: OptimisationConfig,
) -> pd.DataFrame:
    """Return feasible constrained target-return portfolios."""
    minimum = optimise_portfolio("minimum_volatility", means, covariance, risk_free_rate, config)
    # The frontier endpoint with the highest expected return needs a linear objective.
    mean_values = means.reindex(UNIVERSE).to_numpy(dtype=float)
    solution = minimize(
        lambda w: -float(w @ mean_values),
        np.array([0.2, 0.0, 0.0, 0.6, 0.2, 0.0, 0.0]),
        method="SLSQP",
        bounds=_bounds(config),
        constraints=policy_constraints(config),
        options={"ftol": 1e-12, "maxiter": 2_000},
    )
    if not minimum.success or not solution.success:
        raise RuntimeError("Could not establish feasible frontier endpoints")
    maximum_expected = float(solution.x @ mean_values)
    targets = np.linspace(minimum.expected_return, maximum_expected, config.frontier_points)
    rows = []
    for target in targets:
        result = optimise_portfolio(
            "efficient_frontier", means, covariance, risk_free_rate, config, float(target)
        )
        if result.success:
            row = {
                "target_return": target,
                "expected_return": result.expected_return,
                "volatility": result.volatility,
                "sharpe": result.sharpe,
            }
            row.update({f"weight_{ticker}": result.weights[ticker] for ticker in UNIVERSE})
            rows.append(row)
    if len(rows) < 3:
        raise RuntimeError("Efficient frontier produced too few feasible portfolios")
    return pd.DataFrame(rows)
