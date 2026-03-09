"""Attendance journal aggregation for enterprise learner operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AttendanceEntry:
    learner_id: str
    cohort_id: str
    week: int
    attended_minutes: int
    scheduled_minutes: int
    late_join_minutes: int


@dataclass(frozen=True)
class AttendanceSummary:
    cohort_id: str
    attendance_percent: float
    punctuality_percent: float
    at_risk_learners: List[str]


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def summarize_attendance(entries: Iterable[AttendanceEntry], cohort_id: str, week: int) -> AttendanceSummary:
    rows = [item for item in entries if item.cohort_id == cohort_id and item.week == week]
    if not rows:
        return AttendanceSummary(cohort_id=cohort_id, attendance_percent=0.0, punctuality_percent=0.0, at_risk_learners=[])

    total_attended = 0
    total_scheduled = 0
    total_late = 0
    risk: List[str] = []

    for row in rows:
        attended = max(0, row.attended_minutes)
        scheduled = max(0, row.scheduled_minutes)
        late = max(0, row.late_join_minutes)

        total_attended += attended
        total_scheduled += scheduled
        total_late += late

        row_attendance = _rate(attended, scheduled if scheduled > 0 else 1)
        if row_attendance < 70 or late > 20:
            risk.append(row.learner_id)

    punctuality_percent = 100.0 - _rate(total_late, total_scheduled if total_scheduled > 0 else 1)

    return AttendanceSummary(
        cohort_id=cohort_id,
        attendance_percent=_rate(total_attended, total_scheduled if total_scheduled > 0 else 1),
        punctuality_percent=round(max(0.0, punctuality_percent), 2),
        at_risk_learners=sorted(set(risk)),
    )


def cohort_week_trend(entries: Iterable[AttendanceEntry], cohort_id: str) -> Dict[int, float]:
    trend: Dict[int, Dict[str, int]] = {}
    for row in entries:
        if row.cohort_id != cohort_id:
            continue
        if row.week not in trend:
            trend[row.week] = {"attended": 0, "scheduled": 0}
        trend[row.week]["attended"] += max(0, row.attended_minutes)
        trend[row.week]["scheduled"] += max(0, row.scheduled_minutes)

    return {
        week: _rate(values["attended"], values["scheduled"] if values["scheduled"] > 0 else 1)
        for week, values in sorted(trend.items(), key=lambda item: item[0])
    }
