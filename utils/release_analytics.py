"""Analytics helpers for enterprise release telemetry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ReleaseMetricPoint:
    release_id: str
    lead_time_minutes: int
    deployment_minutes: int
    rollback_count: int
    escaped_defects: int


@dataclass(frozen=True)
class ReleaseMetricSummary:
    release_count: int
    avg_lead_time_minutes: float
    avg_deployment_minutes: float
    rollback_rate: float
    defect_rate: float


def _safe_average(values: List[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def summarize_release_metrics(points: Iterable[ReleaseMetricPoint]) -> ReleaseMetricSummary:
    materialized = list(points)

    lead_times = [point.lead_time_minutes for point in materialized]
    deployment_times = [point.deployment_minutes for point in materialized]

    total_rollbacks = sum(point.rollback_count for point in materialized)
    total_defects = sum(point.escaped_defects for point in materialized)

    release_count = len(materialized)

    rollback_rate = 0.0
    defect_rate = 0.0

    if release_count > 0:
        rollback_rate = round(total_rollbacks / release_count, 3)
        defect_rate = round(total_defects / release_count, 3)

    return ReleaseMetricSummary(
        release_count=release_count,
        avg_lead_time_minutes=_safe_average(lead_times),
        avg_deployment_minutes=_safe_average(deployment_times),
        rollback_rate=rollback_rate,
        defect_rate=defect_rate,
    )


def release_health_band(summary: ReleaseMetricSummary) -> str:
    if summary.release_count == 0:
        return "unknown"

    if summary.rollback_rate >= 1.0 or summary.defect_rate >= 2.0:
        return "critical"

    if summary.rollback_rate >= 0.5 or summary.defect_rate >= 1.0:
        return "high"

    if summary.avg_deployment_minutes > 45 or summary.avg_lead_time_minutes > 360:
        return "medium"

    return "low"


def metrics_to_dict(summary: ReleaseMetricSummary) -> Dict[str, float | int | str]:
    return {
        "release_count": summary.release_count,
        "avg_lead_time_minutes": summary.avg_lead_time_minutes,
        "avg_deployment_minutes": summary.avg_deployment_minutes,
        "rollback_rate": summary.rollback_rate,
        "defect_rate": summary.defect_rate,
        "health_band": release_health_band(summary),
    }


def release_trend(points: Iterable[ReleaseMetricPoint]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []

    for point in points:
        score = 100
        score -= min(point.lead_time_minutes // 20, 30)
        score -= min(point.deployment_minutes // 5, 20)
        score -= min(point.rollback_count * 15, 30)
        score -= min(point.escaped_defects * 10, 30)
        score = max(0, score)

        rows.append(
            {
                "release_id": point.release_id,
                "score": score,
                "rollback_count": point.rollback_count,
                "escaped_defects": point.escaped_defects,
            }
        )

    return rows
