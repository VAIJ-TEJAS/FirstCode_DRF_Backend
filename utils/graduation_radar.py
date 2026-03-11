"""Graduation radar and outcome tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class GraduationSignal:
    learner_id: str
    completed_modules: int
    total_modules: int
    capstone_score: float
    placement_ready: bool


@dataclass(frozen=True)
class GraduationSummary:
    total_learners: int
    completion_rate: float
    capstone_avg: float
    placement_ready_rate: float


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def summarize_graduation(signals: Iterable[GraduationSignal]) -> GraduationSummary:
    rows = list(signals)
    if not rows:
        return GraduationSummary(0, 0.0, 0.0, 0.0)

    completed = sum(max(0, row.completed_modules) for row in rows)
    total = sum(max(0, row.total_modules) for row in rows)
    capstone_avg = round(sum(max(0.0, row.capstone_score) for row in rows) / len(rows), 2)
    placement_ready = len([row for row in rows if row.placement_ready])

    return GraduationSummary(
        total_learners=len(rows),
        completion_rate=_rate(completed, total if total > 0 else 1),
        capstone_avg=capstone_avg,
        placement_ready_rate=_rate(placement_ready, len(rows)),
    )


def graduation_heatmap(signals: Iterable[GraduationSignal]) -> Dict[str, float]:
    return {row.learner_id: _rate(row.completed_modules, max(1, row.total_modules)) for row in signals}


def graduation_digest(signals: Iterable[GraduationSignal]) -> Dict[str, object]:
    summary = summarize_graduation(signals)
    return {
        "total_learners": summary.total_learners,
        "completion_rate": summary.completion_rate,
        "capstone_avg": summary.capstone_avg,
        "placement_ready_rate": summary.placement_ready_rate,
        "heatmap": graduation_heatmap(signals),
    }


def completion_pressure(signals: Iterable[GraduationSignal]) -> float:
    summary = summarize_graduation(signals)
    return round((100.0 - summary.completion_rate), 2)


def cohort_completion_map(signals_by_cohort: Dict[str, List[GraduationSignal]]) -> Dict[str, float]:
    return {
        cohort_id: summarize_graduation(rows).completion_rate
        for cohort_id, rows in sorted(signals_by_cohort.items(), key=lambda item: item[0])
    }


def placement_ready_registry(signals: Iterable[GraduationSignal]) -> List[str]:
    return [row.learner_id for row in signals if row.placement_ready]


def capstone_distribution(signals: Iterable[GraduationSignal]) -> Dict[str, int]:
    distribution = {"under_60": 0, "under_80": 0, "over_80": 0}
    for row in signals:
        if row.capstone_score < 60:
            distribution["under_60"] += 1
        elif row.capstone_score < 80:
            distribution["under_80"] += 1
        else:
            distribution["over_80"] += 1
    return distribution
