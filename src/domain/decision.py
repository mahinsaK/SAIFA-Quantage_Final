"""Single source of truth for the committee decision; every deliverable renders from it."""

import json
from dataclasses import dataclass
from pathlib import Path

RECORD = "docs/final/committee-decision.json"

# The only permitted outcomes, with the wording used identically in the app, memo, report and tear sheet.
OUTCOMES = {
    "accept": "Accept as proposed",
    "adjust": "Adjust risk limits",
    "reject": "Reject",
}
MEANING = {
    "accept": "The proposed allocation and review triggers are adopted unchanged.",
    "adjust": "The allocation is adopted only with the stated changes to its risk limits.",
    "reject": "The proposed allocation is not adopted; the stated reason and next step apply.",
}
PENDING = "Pending committee decision"


class DecisionError(ValueError):
    """The decision record is unreadable or inconsistent."""


@dataclass(frozen=True)
class Decision:
    outcome: str | None
    allocation: str = ""
    decided_by: tuple[str, ...] = ()
    decided_on: str = ""
    rationale: str = ""
    changes: str = ""

    @property
    def label(self) -> str:
        return OUTCOMES[self.outcome] if self.outcome else PENDING

    @property
    def statement(self) -> str:
        """The one sentence reused verbatim by the app, memo, report and tear sheet."""
        if not self.outcome:
            return f"{PENDING}: the allocations are research candidates, not a recommendation."
        text = f"Committee decision: {self.label}"
        text += f" (allocation: {self.allocation})." if self.allocation else "."
        if self.outcome == "adjust":
            text += f" Changes: {self.changes}"
        return f"{text} Rationale: {self.rationale}"



def load_decision(root: Path) -> Decision:
    path = root / RECORD
    if not path.exists():
        return Decision(None)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        outcome = raw.get("outcome")
        if outcome is not None and outcome not in OUTCOMES:
            raise DecisionError(f"Outcome must be one of {sorted(OUTCOMES)} or null, not {outcome!r}")
        decision = Decision(
            outcome,
            raw.get("allocation", ""),
            tuple(raw.get("decided_by", ())),
            raw.get("decided_on", ""),
            raw.get("rationale", ""),
            raw.get("changes", ""),
        )
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        if isinstance(exc, DecisionError):
            raise
        raise DecisionError(f"Cannot read {path.name}: {exc}") from exc
    if outcome:
        missing = [
            name
            for name, value in (
                ("decided_by", decision.decided_by),
                ("decided_on", decision.decided_on),
                ("rationale", decision.rationale),
            )
            if not value
        ]
        if outcome == "adjust" and not decision.changes:
            missing.append("changes")
        if missing:
            raise DecisionError(f"A recorded {outcome} decision needs: {', '.join(missing)}")
    return decision
