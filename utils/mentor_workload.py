"""Mentor workload balancing helpers for large cohorts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class MentorLoad:
    mentor_id: str
    cohort_id: str
    learners_assigned: int
    pending_doubts: int
    pending_reviews: int
    avg_response_minutes: int


@dataclass(frozen=True)
class MentorSignal:
    mentor_id: str
    load_score: float
    status: str
    actions: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_mentor(load: MentorLoad) -> MentorSignal:
    score = _clamp(
        load.learners_assigned * 1.2
        + load.pending_doubts * 1.8
        + load.pending_reviews * 1.5
        + (load.avg_response_minutes / 10.0)
    )

    status = "balanced"
    actions: List[str] = []

    if score >= 55:
        status = "watch"
        actions.append("rebalance-doubt-queue")

    if score >= 75:
        status = "overloaded"
        actions.append("assign-backup-mentor")

    if load.avg_response_minutes > 180:
        actions.append("mentor-escalation")

    return MentorSignal(mentor_id=load.mentor_id, load_score=round(score, 2), status=status, actions=actions)


def cohort_load_summary(loads: Iterable[MentorLoad], cohort_id: str) -> Dict[str, int]:
    filtered = [item for item in loads if item.cohort_id == cohort_id]
    summary = {"balanced": 0, "watch": 0, "overloaded": 0}

    for item in filtered:
        signal = evaluate_mentor(item)
        summary[signal.status] += 1

    return summary


def mentors_needing_support(loads: Iterable[MentorLoad]) -> List[str]:
    return [signal.mentor_id for signal in (evaluate_mentor(item) for item in loads) if signal.status != "balanced"]


def team_pressure_map(loads: Iterable[MentorLoad]) -> Dict[str, float]:
    totals: Dict[str, List[float]] = {}
    for row in loads:
        signal = evaluate_mentor(row)
        totals.setdefault(row.cohort_id, []).append(signal.load_score)

    return {
        cohort_id: round(sum(scores) / len(scores), 2) if scores else 0.0
        for cohort_id, scores in sorted(totals.items(), key=lambda item: item[0])
    }


def explain_mentor_signal(load: MentorLoad) -> Dict[str, object]:
    signal = evaluate_mentor(load)
    return {
        "mentor_id": signal.mentor_id,
        "cohort_id": load.cohort_id,
        "learners_assigned": load.learners_assigned,
        "pending_doubts": load.pending_doubts,
        "pending_reviews": load.pending_reviews,
        "avg_response_minutes": load.avg_response_minutes,
        "load_score": signal.load_score,
        "status": signal.status,
        "actions": list(signal.actions),
    }
