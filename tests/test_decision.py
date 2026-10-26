"""The committee decision has one record, three fixed outcomes and no silent defaults."""

import json

import pytest

from src.domain.decision import OUTCOMES, RECORD, DecisionError, load_decision


def write(root, **fields):
    path = root / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(fields))


def test_missing_or_null_record_is_pending(tmp_path):
    assert load_decision(tmp_path).outcome is None
    write(tmp_path, outcome=None)
    decision = load_decision(tmp_path)
    assert decision.label == "Pending committee decision"
    assert "not a recommendation" in decision.statement


@pytest.mark.parametrize("outcome", OUTCOMES)
def test_each_outcome_uses_the_fixed_label(tmp_path, outcome):
    write(
        tmp_path,
        outcome=outcome,
        allocation="Minimum volatility",
        decided_by=["A"],
        decided_on="2026-10-30",
        rationale="Evidence reviewed.",
        changes="Tighten ES limit.",
    )
    decision = load_decision(tmp_path)
    assert decision.label == OUTCOMES[outcome]
    assert decision.statement.startswith(f"Committee decision: {OUTCOMES[outcome]}")


def test_unknown_outcome_and_incomplete_records_fail_closed(tmp_path):
    write(tmp_path, outcome="approve")
    with pytest.raises(DecisionError):
        load_decision(tmp_path)
    write(tmp_path, outcome="accept", decided_by=["A"])
    with pytest.raises(DecisionError, match="decided_on"):
        load_decision(tmp_path)
    write(
        tmp_path, outcome="adjust", decided_by=["A"], decided_on="2026-10-30", rationale="Because."
    )
    with pytest.raises(DecisionError, match="changes"):
        load_decision(tmp_path)
    (tmp_path / RECORD).write_text("not json")
    with pytest.raises(DecisionError):
        load_decision(tmp_path)
