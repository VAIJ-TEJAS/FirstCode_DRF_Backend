"""Enterprise scheduling heuristics for cohort planning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SessionBlock:
    block_id: str
    cohort_id: str
    instructor_id: str
    planned_minutes: int
    day_of_week: int
    start_hour: int


@dataclass(frozen=True)
class ScheduleSummary:
    cohort_id: str
    total_minutes: int
    overload_blocks: int
    instructor_load: Dict[str, int]


def _clamp_minutes(value: int) -> int:
    return max(0, value)


def summarize_schedule(blocks: Iterable[SessionBlock], cohort_id: str) -> ScheduleSummary:
    rows = [item for item in blocks if item.cohort_id == cohort_id]
    total_minutes = 0
    overload_blocks = 0
    instructor_load: Dict[str, int] = {}

    for block in rows:
        minutes = _clamp_minutes(block.planned_minutes)
        total_minutes += minutes
        instructor_load[block.instructor_id] = instructor_load.get(block.instructor_id, 0) + minutes
        if minutes >= 240:
            overload_blocks += 1

    return ScheduleSummary(
        cohort_id=cohort_id,
        total_minutes=total_minutes,
        overload_blocks=overload_blocks,
        instructor_load=instructor_load,
    )


def instructor_hotspots(blocks: Iterable[SessionBlock], threshold_minutes: int = 600) -> List[str]:
    summary: Dict[str, int] = {}
    for block in blocks:
        summary[block.instructor_id] = summary.get(block.instructor_id, 0) + _clamp_minutes(block.planned_minutes)

    return [key for key, value in sorted(summary.items(), key=lambda item: (-item[1], item[0])) if value >= threshold_minutes]


def day_utilization(blocks: Iterable[SessionBlock]) -> Dict[int, int]:
    totals: Dict[int, int] = {}
    for block in blocks:
        totals[block.day_of_week] = totals.get(block.day_of_week, 0) + _clamp_minutes(block.planned_minutes)
    return dict(sorted(totals.items(), key=lambda item: item[0]))


def schedule_density(blocks: Iterable[SessionBlock], cohort_id: str) -> Dict[int, int]:
    filtered = [item for item in blocks if item.cohort_id == cohort_id]
    density: Dict[int, int] = {}
    for block in filtered:
        density[block.day_of_week] = density.get(block.day_of_week, 0) + 1
    return dict(sorted(density.items(), key=lambda item: item[0]))


def cohort_load_map(blocks: Iterable[SessionBlock]) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for block in blocks:
        totals[block.cohort_id] = totals.get(block.cohort_id, 0) + _clamp_minutes(block.planned_minutes)
    return dict(sorted(totals.items(), key=lambda item: item[0]))


def block_heatmap(blocks: Iterable[SessionBlock]) -> Dict[str, int]:
    heatmap: Dict[str, int] = {}
    for block in blocks:
        key = f\"{block.day_of_week}-{block.start_hour}\"
        heatmap[key] = heatmap.get(key, 0) + 1
    return dict(sorted(heatmap.items(), key=lambda item: item[0]))
