"""Grade reconciliation helpers for enterprise gradebook workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class GradeRecord:
    learner_id: str
    source: str
    score: float


@dataclass(frozen=True)
class ReconciliationResult:
    learner_id: str
    canonical_score: float
    variance: float
    requires_review: bool


def reconcile_scores(records: Iterable[GradeRecord], review_threshold: float = 12.0) -> List[ReconciliationResult]:
    by_learner: Dict[str, List[float]] = {}

    for record in records:
        by_learner.setdefault(record.learner_id, []).append(float(record.score))

    results: List[ReconciliationResult] = []

    for learner_id, values in sorted(by_learner.items()):
        if not values:
            continue

        canonical = sum(values) / len(values)
        variance = max(values) - min(values)
        requires_review = variance > review_threshold

        results.append(
            ReconciliationResult(
                learner_id=learner_id,
                canonical_score=round(canonical, 2),
                variance=round(variance, 2),
                requires_review=requires_review,
            )
        )

    return results


def review_count(results: Iterable[ReconciliationResult]) -> int:
    return sum(1 for item in results if item.requires_review)
