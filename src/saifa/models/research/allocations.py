"""Empirical CVaR linear programming and policy-constrained risk balancing."""

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.optimize import linprog, minimize

from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.domain.portfolio import OptimisationResult
from saifa.models.optimisation import (
    _bounds,
    annualised_inputs,
    policy_constraints,
    validate_policy_weights,
)
from saifa.models.risk import empirical_tail


def funded_weights(values, policy: OptimisationConfig) -> pd.Series:
    weights = pd.Series(values, index=UNIVERSE, dtype=float)
    weights[weights.abs() < 1e-10] = 0
    validate_policy_weights(weights, policy)
    weights /= weights.sum()
    validate_policy_weights(weights, policy)
    return weights


def minimum_es(
    returns: pd.DataFrame, policy: OptimisationConfig, confidence: float = 0.95
) -> tuple[pd.Series, dict]:
    """Minimise eta + mean(max(loss-eta,0))/(1-confidence), with the same policy."""
    annualised_inputs(returns, policy.annual_trading_days)
    if not np.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("Invalid ES confidence")
    n, k = returns.shape
    objective = np.r_[np.zeros(k), 1.0, np.full(n, 1 / (n * (1 - confidence)))]
    loss_constraints = sparse.hstack(
        [-sparse.csr_matrix(returns.to_numpy()), -np.ones((n, 1)), -sparse.eye(n)], format="csr"
    )
    # Funding is an equality; policy inequalities match the original optimiser.
    rules = np.zeros((3, k + 1 + n))
    rules[0, UNIVERSE.index("AGG")] = -1
    rules[1, [UNIVERSE.index(t) for t in ("SPY", "EFA", "EEM", "XLE", "XLK")]] = 1
    rules[2, [UNIVERSE.index(t) for t in ("XLE", "XLK")]] = 1
    result = linprog(
        objective,
        A_ub=sparse.vstack([loss_constraints, sparse.csr_matrix(rules)]),
        b_ub=np.r_[
            np.zeros(n),
            -policy.bond_minimum,
            policy.equity_maximum,
            policy.sectors_combined_maximum,
        ],
        A_eq=sparse.csr_matrix(np.r_[np.ones(k), np.zeros(1 + n)][None, :]),
        b_eq=[1.0],
        bounds=[*_bounds(policy), (None, None), *[(0, None)] * n],
        method="highs",
    )
    if not result.success:
        raise RuntimeError(f"Minimum ES solver failed: {result.message}")
    weights = funded_weights(result.x[:k], policy)
    actual = empirical_tail(-returns.to_numpy() @ weights.to_numpy(), confidence).es_fraction
    if not np.isclose(actual, result.fun, atol=1e-8, rtol=1e-6):
        raise RuntimeError("LP objective does not reconcile with empirical ES")
    return weights, {
        "objective": "minimum_es",
        "training_es_fraction": actual,
        "confidence": confidence,
        "solver_success": True,
        "message": result.message,
    }


def variance_risk_shares(weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    variance = float(weights @ covariance @ weights)
    if not np.isfinite(variance) or variance <= 0:
        raise ValueError("Risk balancing needs positive portfolio variance")
    return weights * (covariance @ weights) / variance


def constrained_risk_parity(
    covariance: pd.DataFrame, policy: OptimisationConfig
) -> tuple[pd.Series, dict]:
    cov = covariance.loc[list(UNIVERSE), list(UNIVERSE)].to_numpy(dtype=float)
    if (
        not np.isfinite(cov).all()
        or not np.allclose(cov, cov.T)
        or np.linalg.eigvalsh(cov).min() < -1e-10
    ):
        raise ValueError("Risk balancing needs a finite symmetric PSD covariance")
    target = 1 / len(UNIVERSE)

    def objective(w):
        return float(np.square(variance_risk_shares(w, cov) - target).sum())

    starts = ([0.2, 0, 0, 0.6, 0.2, 0, 0], [0.2, 0.02, 0.02, 0.5, 0.16, 0.05, 0.05])
    solutions = [
        minimize(
            objective,
            np.array(start),
            method="SLSQP",
            bounds=_bounds(policy),
            constraints=policy_constraints(policy),
            options={"ftol": 1e-12, "maxiter": 2000},
        )
        for start in starts
    ]
    valid = [r for r in solutions if r.success]
    if not valid:
        raise RuntimeError("Constrained risk-parity solver failed at both deterministic starts")
    result = min(valid, key=lambda r: r.fun)
    weights = funded_weights(result.x, policy)
    shares = variance_risk_shares(weights.to_numpy(), cov)
    error = float(np.max(np.abs(shares - target)))
    return weights, {
        "objective": "risk_parity",
        "solver_success": True,
        "equal_risk_achieved": error < 1e-4,
        "maximum_risk_share_gap": error,
        "message": "Policy-constrained squared risk-share balancing; global optimality is not established. "
        + result.message,
    }


def checked_optimisation(result: OptimisationResult, policy: OptimisationConfig) -> pd.Series:
    if not result.success:
        raise RuntimeError(result.message)
    return funded_weights(result.weights.to_numpy(), policy)
