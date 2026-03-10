from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class ScheduleDemand:
    cohort_id: str
    learners: int
    preferred_window: str


@dataclass(frozen=True)
class ScheduleSupply:
    instructor_id: str
    capacity: int
    windows: List[str]


@dataclass(frozen=True)
class ScheduleAssignment:
    cohort_id: str
    instructor_id: str
    window: str
    learners: int


def allocate_schedule(demands: Iterable[ScheduleDemand], supplies: Iterable[ScheduleSupply]) -> List[ScheduleAssignment]:
    assignments: List[ScheduleAssignment] = []
    supply_state = [
        {"instructor_id": supply.instructor_id, "capacity": supply.capacity, "windows": supply.windows}
        for supply in supplies
    ]

    for demand in demands:
        for supply in supply_state:
            if supply["capacity"] < demand.learners:
                continue
            if demand.preferred_window not in supply["windows"]:
                continue
            supply["capacity"] -= demand.learners
            assignments.append(ScheduleAssignment(
                cohort_id=demand.cohort_id,
                instructor_id=supply["instructor_id"],
                window=demand.preferred_window,
                learners=demand.learners,
            ))
            break

    return assignments


def schedule_coverage(assignments: Iterable[ScheduleAssignment], demands: Iterable[ScheduleDemand]) -> dict:
    assigned = {assignment.cohort_id for assignment in assignments}
    total = list(demands)
    covered = sum(1 for demand in total if demand.cohort_id in assigned)
    return {
        "covered": covered,
        "total": len(total),
        "coverage_rate": 0 if len(total) == 0 else round((covered / len(total)) * 100),
    }
