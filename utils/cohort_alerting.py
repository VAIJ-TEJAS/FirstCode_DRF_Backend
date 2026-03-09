"""Cohort alerting utilities for enterprise operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CohortMetric:
    cohort_id: str
    attendance_rate: float
    assignment_completion_rate: float
    average_exam_score: float


@dataclass(frozen=True)
class CohortAlert:
    cohort_id: str
    severity: str
    message: str


def _severity(attendance: float, completion: float, score: float) -> str:
    if attendance < 50 or completion < 45 or score < 40:
        return "critical"
    if attendance < 65 or completion < 60 or score < 55:
        return "high"
    if attendance < 75 or completion < 70 or score < 65:
        return "medium"
    return "low"


def build_cohort_alerts(metrics: Iterable[CohortMetric]) -> List[CohortAlert]:
    alerts: List[CohortAlert] = []

    for metric in metrics:
        severity = _severity(metric.attendance_rate, metric.assignment_completion_rate, metric.average_exam_score)
        if severity == "low":
            continue

        message = (
            f"Cohort {metric.cohort_id} is {severity}: "
            f"attendance={metric.attendance_rate:.1f}, "
            f"completion={metric.assignment_completion_rate:.1f}, "
            f"score={metric.average_exam_score:.1f}"
        )

        alerts.append(
            CohortAlert(
                cohort_id=metric.cohort_id,
                severity=severity,
                message=message,
            )
        )

    return sorted(
        alerts,
        key=lambda alert: (
            {"critical": 4, "high": 3, "medium": 2}.get(alert.severity, 1) * -1,
            alert.cohort_id,
        ),
    )


def alert_summary(alerts: Iterable[CohortAlert]) -> Dict[str, int]:
    summary = {"critical": 0, "high": 0, "medium": 0}

    for alert in alerts:
        summary[alert.severity] = summary.get(alert.severity, 0) + 1

    return summary
