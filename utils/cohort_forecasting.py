"""Cohort forecasting helpers for enterprise operations."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CohortSnapshot:
    cohort_id: str
    week: int
    active_learners: int
    placements: int
    churned: int


@dataclass(frozen=True)
class CohortForecast:
    cohort_id: str
    expected_placements: int
    churn_rate: float
    confidence: str


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def forecast_cohort(cohort_id: str, snapshots: Iterable[CohortSnapshot]) -> CohortForecast:
    rows = [item for item in snapshots if item.cohort_id == cohort_id]
    if not rows:
        return CohortForecast(cohort_id, 0, 0.0, "low")

    placement_rates = [_rate(item.placements, max(1, item.active_learners)) for item in rows]
    churn_rates = [_rate(item.churned, max(1, item.active_learners)) for item in rows]

    avg_placement = round(mean(placement_rates), 2)
    avg_churn = round(mean(churn_rates), 2)

    active = sum(max(0, item.active_learners) for item in rows)
    expected = int(round((active / max(1, len(rows))) * (avg_placement / 100.0) * (1 - avg_churn / 100.0)))

    confidence = "high" if active >= 200 else "medium" if active >= 100 else "low"

    return CohortForecast(cohort_id, max(0, expected), avg_churn, confidence)


def cohort_mix(snapshots: Iterable[CohortSnapshot]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in snapshots:
        counts[row.cohort_id] = counts.get(row.cohort_id, 0) + 1
    return counts


def forecast_matrix(snapshots: Iterable[CohortSnapshot]) -> Dict[str, CohortForecast]:
    cohorts = sorted({row.cohort_id for row in snapshots})
    return {cohort_id: forecast_cohort(cohort_id, snapshots) for cohort_id in cohorts}


def placement_trend(snapshots: Iterable[CohortSnapshot], cohort_id: str) -> Dict[int, int]:
    rows = [row for row in snapshots if row.cohort_id == cohort_id]
    return {row.week: max(0, row.placements) for row in sorted(rows, key=lambda item: item.week)}


def churn_trend(snapshots: Iterable[CohortSnapshot], cohort_id: str) -> Dict[int, int]:
    rows = [row for row in snapshots if row.cohort_id == cohort_id]
    return {row.week: max(0, row.churned) for row in sorted(rows, key=lambda item: item.week)}


def confidence_map(snapshots: Iterable[CohortSnapshot]) -> Dict[str, str]:
    cohorts = sorted({row.cohort_id for row in snapshots})
    return {cohort_id: forecast_cohort(cohort_id, snapshots).confidence for cohort_id in cohorts}
