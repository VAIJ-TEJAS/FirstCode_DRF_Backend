"""Student health indexing for enterprise intervention workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class StudentHealthSignal:
    learner_id: str
    attendance_rate: float
    assignment_completion_rate: float
    exam_score_average: float
    support_tickets_last_30d: int


@dataclass(frozen=True)
class StudentHealthScore:
    learner_id: str
    score: float
    band: str
    risk_flags: List[str]


def _clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(max_value, float(value)))


def _band(score: float) -> str:
    if score >= 80:
        return "green"
    if score >= 60:
        return "yellow"
    if score >= 40:
        return "orange"
    return "red"


def build_student_health_score(signal: StudentHealthSignal) -> StudentHealthScore:
    attendance = _clamp(signal.attendance_rate, 0, 100)
    completion = _clamp(signal.assignment_completion_rate, 0, 100)
    exams = _clamp(signal.exam_score_average, 0, 100)

    score = attendance * 0.35 + completion * 0.3 + exams * 0.35

    risk_flags: List[str] = []
    if attendance < 65:
        risk_flags.append("attendance-risk")
    if completion < 65:
        risk_flags.append("completion-risk")
    if exams < 55:
        risk_flags.append("exam-risk")
    if signal.support_tickets_last_30d >= 4:
        risk_flags.append("support-load-risk")

    score -= min(12, signal.support_tickets_last_30d * 2)
    score = _clamp(score, 0, 100)

    return StudentHealthScore(
        learner_id=signal.learner_id,
        score=round(score, 2),
        band=_band(score),
        risk_flags=risk_flags,
    )


def summarize_health_bands(items: Iterable[StudentHealthScore]) -> Dict[str, int]:
    summary = {"green": 0, "yellow": 0, "orange": 0, "red": 0}

    for item in items:
        summary[item.band] = summary.get(item.band, 0) + 1

    return summary
