from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class RunbookStep:
    step_id: str
    action: str
    owner: str
    sla_hours: int


def runbook_timeline(steps: Iterable[RunbookStep]) -> dict:
    steps_list = list(steps)
    return {
        "steps": len(steps_list),
        "total_sla": sum(step.sla_hours for step in steps_list),
    }


def runbook_owners(steps: Iterable[RunbookStep]) -> List[str]:
    return sorted({step.owner for step in steps})
