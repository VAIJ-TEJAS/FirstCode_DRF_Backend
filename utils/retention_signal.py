"""Retention signal and intervention scoring utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class RetentionInput:
    learner_id: str
    attendance_percent: float
    assignment_completion_percent: float
    quiz_average: float
    mentor_response_sla_percent: float


@dataclass(frozen=True)
class RetentionSignal:
    learner_id: str
    score: float
    band: str
    interventions: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _band(score: float) -> str:
    if score >= 85:
        return "stable"
    if score >= 70:
        return "watch"
    if score >= 50:
        return "at_risk"
    return "critical"


def evaluate_retention(row: RetentionInput) -> RetentionSignal:
    score = _clamp(
        row.attendance_percent * 0.35
        + row.assignment_completion_percent * 0.25
        + row.quiz_average * 0.20
        + row.mentor_response_sla_percent * 0.20
    )

    band = _band(score)
    interventions: List[str] = []

    if row.attendance_percent < 75:
        interventions.append("attendance-recovery-plan")
    if row.assignment_completion_percent < 70:
        interventions.append("assignment-catchup-sprint")
    if row.quiz_average < 60:
        interventions.append("concept-remediation-bootcamp")
    if row.mentor_response_sla_percent < 70:
        interventions.append("mentor-escalation")

    if band == "critical" and "mentor-escalation" not in interventions:
        interventions.append("mentor-escalation")

    return RetentionSignal(
        learner_id=row.learner_id,
        score=round(score, 2),
        band=band,
        interventions=interventions,
    )


def summarize_bands(signals: Iterable[RetentionSignal]) -> Dict[str, int]:
    summary = {"stable": 0, "watch": 0, "at_risk": 0, "critical": 0}
    for signal in signals:
        summary[signal.band] += 1
    return summary
