"""Independent feasibility/objective checks and development-only perturbations."""

from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from saifa.domain.config import UNIVERSE, OptimisationConfig
from saifa.domain.research import ResearchConfig
from saifa.models.optimisation import validate_policy_weights
from saifa.models.research.allocations import (
    constrained_risk_parity,
    minimum_es,
    variance_risk_shares,
)
from saifa.models.research.robustness import allocation_robustness, block_indices


def test_minimum_es_matches_known_linear_bound_and_empirical_tail():
    # Every asset loses 1%, except AGG which loses 0.5%. Its 60% cap makes
    # 0.6*0.005 + 0.4*0.01 = 0.007 the attainable minimum loss/ES.
    returns = pd.DataFrame(-0.01, index=pd.bdate_range("2010-01-01", periods=252), columns=UNIVERSE)
    returns["AGG"] = -0.005
    weights, details = minimum_es(returns, OptimisationConfig(), 0.95)
    validate_policy_weights(weights, OptimisationConfig())
    assert weights.AGG == pytest.approx(0.6)
    assert details["training_es_fraction"] == pytest.approx(0.007)


def test_risk_parity_equal_variances_unconstrained_and_policy_limited():
    covariance = pd.DataFrame(np.eye(7), index=UNIVERSE, columns=UNIVERSE)
    relaxed = replace(
        OptimisationConfig(),
        bond_minimum=0,
        single_asset_maximum=1,
        equity_maximum=1,
        gold_maximum=1,
        sector_maximum=1,
        sectors_combined_maximum=1,
    )
    weights, details = constrained_risk_parity(covariance, relaxed)
    assert weights.to_numpy() == pytest.approx(np.full(7, 1 / 7), abs=2e-5)
    assert details["equal_risk_achieved"]
    assert variance_risk_shares(weights.to_numpy(), np.eye(7)).sum() == pytest.approx(1)
    limited, detail = constrained_risk_parity(covariance, OptimisationConfig())
    validate_policy_weights(limited, OptimisationConfig())
    assert not detail["equal_risk_achieved"]
    assert detail["maximum_risk_share_gap"] > 0.01


def test_invalid_covariance_and_confidence_are_rejected():
    bad = pd.DataFrame(np.eye(7), index=UNIVERSE, columns=UNIVERSE)
    bad.iloc[0, 0] = -1
    with pytest.raises(ValueError):
        constrained_risk_parity(bad, OptimisationConfig())
    returns = pd.DataFrame(0.001, index=pd.bdate_range("2010-01-01", periods=252), columns=UNIVERSE)
    with pytest.raises(ValueError):
        minimum_es(returns, OptimisationConfig(), 1)


def test_block_resampling_repeats_seed_and_cannot_bridge_calendar_gaps():
    continuity = np.array([True, False, True, False])
    indices = block_indices(4, 100, 20, 1000, 15, continuity)
    assert np.array_equal(indices, block_indices(4, 100, 20, 1000, 15, continuity))
    # Force continuation to be impossible at every row: the next draw must be a
    # new random start rather than deterministically walking across a missing month.
    all_gaps = block_indices(4, 100, 20, 1000, 15, np.zeros(4, dtype=bool))
    assert np.mean(all_gaps[:, 1:] == (all_gaps[:, :-1] + 1) % 4) < 0.4
    assert indices.min() >= 0 and indices.max() < 4


def test_robustness_cannot_use_evaluation_rows_or_rates():
    dates = pd.bdate_range("2004-01-01", "2020-12-31")
    rng = np.random.default_rng(45)
    returns = pd.DataFrame(rng.normal(0.0003, 0.01, (len(dates), 7)), index=dates, columns=UNIVERSE)
    rates = pd.Series(0.0001, index=dates)
    reference = pd.DataFrame(
        [[0.4, 0, 0, 0.6, 0, 0, 0], [0.4, 0, 0, 0.6, 0, 0, 0]],
        index=["minimum_volatility", "maximum_sharpe"],
        columns=UNIVERSE,
    )
    settings = ResearchConfig(robustness_replicates=2)
    original = allocation_robustness(returns, rates, reference, OptimisationConfig(), settings)
    returns.loc["2019":] += 0.2
    rates.loc["2019":] = 0.5
    changed = allocation_robustness(returns, rates, reference, OptimisationConfig(), settings)
    pd.testing.assert_frame_equal(original, changed)
    assert original.status.eq("ok").all()
    for _, row in original.iterrows():
        validate_policy_weights(row.loc[list(UNIVERSE)].astype(float), OptimisationConfig())
