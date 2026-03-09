"""Outcome audit helpers for enterprise learning operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class OutcomeRecord:
    learner_id: str
    course_id: str
    baseline_score: float
    final_score: float
    completed: bool


@dataclass(frozen=True)
class OutcomeAuditSnapshot:
    learner_count: int
    completion_rate: float
    average_gain: float
    negative_gain_count: int
    status: str


def _status(completion_rate: float, average_gain: float, negative_gain_count: int) -> str:
    if completion_rate < 55 or average_gain < 5 or negative_gain_count >= 10:
        return "critical"
    if completion_rate < 70 or average_gain < 10 or negative_gain_count >= 5:
        return "watch"
    return "healthy"


def build_outcome_audit(records: Iterable[OutcomeRecord]) -> OutcomeAuditSnapshot:
    rows = list(records)

    learner_count = len(rows)
    if learner_count == 0:
        return OutcomeAuditSnapshot(0, 0.0, 0.0, 0, "critical")

    completed = sum(1 for row in rows if row.completed)
    completion_rate = round((completed / learner_count) * 100, 2)

    gains: List[float] = []
    negative_gain_count = 0

    for row in rows:
        gain = row.final_score - row.baseline_score
        gains.append(gain)
        if gain < 0:
            negative_gain_count += 1

    average_gain = round(sum(gains) / learner_count, 2)

    return OutcomeAuditSnapshot(
        learner_count=learner_count,
        completion_rate=completion_rate,
        average_gain=average_gain,
        negative_gain_count=negative_gain_count,
        status=_status(completion_rate, average_gain, negative_gain_count),
    )


def course_level_gains(records: Iterable[OutcomeRecord]) -> Dict[str, float]:
    aggregates: Dict[str, List[float]] = {}

    for row in records:
        aggregates.setdefault(row.course_id, []).append(row.final_score - row.baseline_score)

    return {
        course_id: round(sum(gains) / len(gains), 2)
        for course_id, gains in sorted(aggregates.items())
        if gains
    }
