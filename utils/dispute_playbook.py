from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class DisputeCase:
    dispute_id: str
    amount: float
    reason: str
    evidence_count: int


def dispute_priority(case: DisputeCase) -> str:
    if case.amount >= 50000 or case.reason == "compliance":
        return "critical"
    if case.amount >= 15000:
        return "elevated"
    return "standard"


def dispute_actions(case: DisputeCase) -> List[str]:
    actions = ["acknowledge", "assign_owner"]
    if case.evidence_count == 0:
        actions.append("request_evidence")
    if dispute_priority(case) == "critical":
        actions.append("exec_review")
    return actions
