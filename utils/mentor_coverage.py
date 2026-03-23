"""Mentor coverage tracking helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, TypedDict


@dataclass(frozen=True)
class MentorCoverage:
    mentor_id: str
    learners_assigned: int
    hours_available: int
    sessions_scheduled: int


@dataclass(frozen=True)
class CoverageScore:
    mentor_id: str
    utilization_percent: float
    status: str


class CoverageDigest(TypedDict):
    summary: Dict[str, int]
    heatmap: Dict[str, float]
    pressure: float
    overloaded: List[str]
    alerts: List[str]


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def evaluate_coverage(row: MentorCoverage) -> CoverageScore:
    capacity = max(1, row.hours_available) * 4
    utilization = _rate(row.sessions_scheduled, capacity)

    status = "balanced"
    if utilization >= 85:
        status = "watch"
    if utilization >= 100:
        status = "overloaded"

    return CoverageScore(row.mentor_id, utilization, status)


def coverage_summary(rows: Iterable[MentorCoverage]) -> Dict[str, int]:
    summary = {"balanced": 0, "watch": 0, "overloaded": 0}
    for row in rows:
        summary[evaluate_coverage(row).status] += 1
    return summary


def coverage_heatmap(rows: Iterable[MentorCoverage]) -> Dict[str, float]:
    return {row.mentor_id: evaluate_coverage(row).utilization_percent for row in rows}


def coverage_forecast(rows: Iterable[MentorCoverage], weeks: int = 4) -> Dict[int, Dict[str, int]]:
    summary = coverage_summary(rows)
    projection: Dict[int, Dict[str, int]] = {}
    for week in range(1, max(1, weeks) + 1):
        projection[week] = {
            "balanced": max(0, summary["balanced"] - week // 2),
            "watch": summary["watch"],
            "overloaded": summary["overloaded"],
        }
    return projection


def utilization_map(rows: Iterable[MentorCoverage]) -> Dict[str, float]:
    return {row.mentor_id: evaluate_coverage(row).utilization_percent for row in rows}


def coverage_pressure(rows: Iterable[MentorCoverage]) -> float:
    utilizations = list(utilization_map(rows).values())
    if not utilizations:
        return 0.0
    return round(sum(utilizations) / len(utilizations), 2)


def coverage_alerts(rows: Iterable[MentorCoverage]) -> List[str]:
    alerts: List[str] = []
    for row in rows:
        if evaluate_coverage(row).status == "overloaded":
            alerts.append(row.mentor_id)
    return alerts


def coverage_digest(rows: Iterable[MentorCoverage]) -> CoverageDigest:
    # Materialize once so all downstream calculations are stable even if `rows` is a generator.
    normalized_rows = list(rows)
    summary = coverage_summary(normalized_rows)
    heatmap = coverage_heatmap(normalized_rows)
    alerts = coverage_alerts(normalized_rows)

    return {
        "summary": summary,
        "heatmap": heatmap,
        "pressure": coverage_pressure(normalized_rows),
        "overloaded": alerts,
        "alerts": alerts,
    }
