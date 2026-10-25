"""Kupiec coverage, Christoffersen independence and the canonical Basel diagnostic."""

import numpy as np
from scipy.special import xlogy
from scipy.stats import binomtest, chi2

from saifa.domain.backtesting import CoverageResult, IndependenceResult, TrafficLight


def _hits(values) -> np.ndarray:
    hits = np.asarray(values, dtype=float)
    if hits.ndim != 1 or not np.all(np.isnan(hits) | (hits == 0) | (hits == 1)):
        raise ValueError("Exceptions must be a one-dimensional sequence of 0, 1, or missing")
    return hits


def _probability(value: float, name: str) -> None:
    if not np.isfinite(value) or not 0 < value < 1:
        raise ValueError(f"{name} must be a finite fraction in (0, 1)")


def _log_likelihood(zeros: int, ones: int, probability: float) -> float:
    # xlogy(0, 0) = 0 implements the continuous likelihood limit at boundary MLEs.
    return float(xlogy(zeros, 1 - probability) + xlogy(ones, probability))


def kupiec_test(exceptions, confidence: float, significance: float = 0.05) -> CoverageResult:
    hits = _hits(exceptions)
    _probability(confidence, "Confidence")
    _probability(significance, "Significance")
    valid = int(np.isfinite(hits).sum())
    count = int(np.nansum(hits))
    missing = len(hits) - valid
    base = {
        "observations": len(hits),
        "valid_forecasts": valid,
        "missing_forecasts": missing,
        "exceptions": count,
        "expected_exceptions": len(hits) * (1 - confidence),
        "exception_rate": count / valid if valid else None,
    }
    if not valid or missing:
        return CoverageResult(
            **base,
            statistic=None,
            p_value=None,
            exact_p_value=None,
            decision="unavailable",
            warning="Empty or incomplete forecast sequence; no dropped-day test",
        )
    rate = count / valid
    statistic = max(
        0.0,
        2
        * (
            _log_likelihood(valid - count, count, rate)
            - _log_likelihood(valid - count, count, 1 - confidence)
        ),
    )
    p_value = float(chi2.sf(statistic, 1))
    exact = float(binomtest(count, valid, 1 - confidence, alternative="two-sided").pvalue)
    warnings = []
    if min(valid * (1 - confidence), valid * confidence) < 5 or count in (0, valid):
        warnings.append(
            "Sparse/boundary counts: chi-square approximation may be weak; see exact binomial p-value"
        )
    warnings.append(
        "Non-rejection does not establish calibration; exact binomial also assumes independence"
    )
    return CoverageResult(
        **base,
        statistic=statistic,
        p_value=p_value,
        exact_p_value=exact,
        decision="reject" if p_value < significance else "do_not_reject",
        warning="; ".join(warnings),
    )


def christoffersen_test(
    exceptions, significance: float = 0.05, minimum_previous_state: int = 5
) -> IndependenceResult:
    hits = _hits(exceptions)
    _probability(significance, "Significance")
    if type(minimum_previous_state) is not int or minimum_previous_state < 1:
        raise ValueError("Minimum previous-state count must be positive")
    # Never join observations across an unavailable forecast.
    left, right = hits[:-1], hits[1:]
    n00, n01, n10, n11 = (
        int(np.sum((left == i) & (right == j))) for i, j in ((0, 0), (0, 1), (1, 0), (1, 1))
    )
    base = {"n00": n00, "n01": n01, "n10": n10, "n11": n11}
    if np.isnan(hits).any() or min(n00 + n01, n10 + n11) < minimum_previous_state:
        return IndependenceResult(
            **base,
            statistic=None,
            p_value=None,
            decision="unavailable",
            warning="Incomplete sequence or insufficient transitions from each previous state",
        )
    pi01, pi11 = n01 / (n00 + n01), n11 / (n10 + n11)
    pooled = (n01 + n11) / (n00 + n01 + n10 + n11)
    alternative = _log_likelihood(n00, n01, pi01) + _log_likelihood(n10, n11, pi11)
    null = _log_likelihood(n00 + n10, n01 + n11, pooled)
    statistic = max(0.0, 2 * (alternative - null))
    p_value = float(chi2.sf(statistic, 1))
    warning = "First-order independence only; non-rejection is not proof of independence"
    expected = np.array([n00 + n01, n10 + n11])[:, None] * np.array([1 - pooled, pooled])
    if expected.min() < 5:
        warning += "; sparse expected transition cells: asymptotic p-value requires caution"
    return IndependenceResult(
        **base,
        statistic=statistic,
        p_value=p_value,
        decision="reject" if p_value < significance else "do_not_reject",
        warning=warning,
    )


def basel_traffic_light(exceptions, confidence: float) -> TrafficLight:
    hits = _hits(exceptions)
    _probability(confidence, "Confidence")
    if not np.isclose(confidence, 0.99, rtol=0, atol=1e-12):
        return TrafficLight(
            len(hits), None, None, "unsupported_confidence", "Requires 99% confidence"
        )
    if len(hits) != 250:
        return TrafficLight(
            len(hits),
            None,
            None,
            "insufficient_window",
            "Requires exactly 250 consecutive sessions",
        )
    if np.isnan(hits).any():
        return TrafficLight(
            250,
            None,
            None,
            "incomplete_forecasts",
            "Missing forecasts inside the 250-session window",
        )
    count = int(hits.sum())
    zone = "green" if count <= 4 else "yellow" if count <= 9 else "red"
    return TrafficLight(
        250,
        count,
        zone,
        "ok",
        "Historical Basel diagnostic; not a regulatory compliance assessment",
    )
