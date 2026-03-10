from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HandoffStep:
    step_id: str
    action: str
    owner: str
    sla_hours: int


def handoff_timeline(steps: Iterable[HandoffStep]) -> dict:
    steps_list = list(steps)
    return {
        "steps": len(steps_list),
        "total_sla": sum(step.sla_hours for step in steps_list),
    }


def handoff_owners(steps: Iterable[HandoffStep]) -> list[str]:
    return sorted({step.owner for step in steps})
