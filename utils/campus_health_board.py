"""Campus health scorecard helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CampusMetric:
    campus_id: str
    attendance_percent: float
    satisfaction_percent: float
    placement_percent: float
    compliance_percent: float


@dataclass(frozen=True)
class CampusHealth:
    campus_id: str
    score: float
    tier: str
    actions: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _tier(score: float) -> str:
    if score >= 85:
        return "strong"
    if score >= 70:
        return "stable"
    if score >= 55:
        return "watch"
    return "critical"


def evaluate_campus(metric: CampusMetric) -> CampusHealth:
    score = _clamp(
        metric.attendance_percent * 0.25
        + metric.satisfaction_percent * 0.25
        + metric.placement_percent * 0.30
        + metric.compliance_percent * 0.20
    )

    tier = _tier(score)
    actions: List[str] = []

    if tier == "watch":
        actions.append("launch-campus-recovery-plan")
    if tier == "critical":
        actions.append("trigger-exec-review")
        actions.append("freeze-new-intake")

    return CampusHealth(campus_id=metric.campus_id, score=round(score, 2), tier=tier, actions=actions)


def summarize_campuses(metrics: Iterable[CampusMetric]) -> Dict[str, int]:
    summary = {"strong": 0, "stable": 0, "watch": 0, "critical": 0}
    for item in metrics:
        summary[evaluate_campus(item).tier] += 1
    return summary


def critical_campuses(metrics: Iterable[CampusMetric]) -> List[str]:
    return [item.campus_id for item in metrics if evaluate_campus(item).tier == "critical"]


def campus_rankings(metrics: Iterable[CampusMetric]) -> List[CampusHealth]:
    return sorted([evaluate_campus(item) for item in metrics], key=lambda row: row.score, reverse=True)


def action_matrix(metrics: Iterable[CampusMetric]) -> Dict[str, List[str]]:
    matrix: Dict[str, List[str]] = {}
    for item in metrics:
        result = evaluate_campus(item)
        matrix[item.campus_id] = list(result.actions)
    return matrix


def portfolio_health(metrics: Iterable[CampusMetric]) -> Dict[str, object]:
    rows = list(metrics)
    if not rows:
        return {
            "average_score": 0.0,
            "tier_summary": {"strong": 0, "stable": 0, "watch": 0, "critical": 0},
            "critical_campuses": [],
        }

    ranked = campus_rankings(rows)
    avg_score = round(sum(item.score for item in ranked) / len(ranked), 2)

    return {
        "average_score": avg_score,
        "tier_summary": summarize_campuses(rows),
        "critical_campuses": critical_campuses(rows),
        "top_campus": ranked[0].campus_id,
        "action_matrix": action_matrix(rows),
    }
