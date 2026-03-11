"""Learning blocker scoring for remediation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class BlockerSignal:
    learner_id: str
    attendance_rate: float
    assessment_avg: float
    mentor_response_hours: float
    late_submissions: int


@dataclass(frozen=True)
class BlockerScore:
    learner_id: str
    score: float
    band: str
    blockers: List[str]


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


def evaluate_blocker(signal: BlockerSignal) -> BlockerScore:
    score = _clamp(
        signal.attendance_rate * 0.35
        + signal.assessment_avg * 0.35
        + (100.0 - signal.mentor_response_hours) * 0.2
        + max(0.0, 100.0 - signal.late_submissions * 4.0) * 0.1
    )

    blockers: List[str] = []
    if signal.attendance_rate < 75:
        blockers.append("attendance-risk")
    if signal.assessment_avg < 60:
        blockers.append("assessment-risk")
    if signal.mentor_response_hours > 48:
        blockers.append("mentor-lag")
    if signal.late_submissions > 3:
        blockers.append("late-submission")

    return BlockerScore(signal.learner_id, round(score, 2), _band(score), blockers)


def blocker_summary(scores: Iterable[BlockerScore]) -> Dict[str, int]:
    summary = {"stable": 0, "watch": 0, "at_risk": 0, "critical": 0}
    for score in scores:
        summary[score.band] += 1
    return summary


def blocker_registry(scores: Iterable[BlockerScore]) -> Dict[str, List[str]]:
    registry: Dict[str, List[str]] = {}
    for score in scores:
        for blocker in score.blockers:
            registry.setdefault(blocker, []).append(score.learner_id)
    return registry


def blocker_priority(scores: Iterable[BlockerScore], limit: int = 5) -> List[BlockerScore]:
    ranked = sorted(
        list(scores),
        key=lambda item: (
            0 if item.band == "critical" else 1 if item.band == "at_risk" else 2 if item.band == "watch" else 3,
            item.score,
        ),
    )
    return ranked[: max(0, limit)]


def blocker_digest(scores: Iterable[BlockerScore]) -> Dict[str, object]:
    rows = list(scores)
    if not rows:
        return {"total": 0, "average_score": 0.0, "band_summary": blocker_summary([]), "registry": {}}

    average_score = round(sum(score.score for score in rows) / len(rows), 2)
    return {
        "total": len(rows),
        "average_score": average_score,
        "band_summary": blocker_summary(rows),
        "registry": blocker_registry(rows),
        "priority": [item.learner_id for item in blocker_priority(rows)],
    }


def blocker_heatmap(scores: Iterable[BlockerScore]) -> Dict[str, float]:
    return {score.learner_id: score.score for score in scores}


def simulate_recovery(scores: Iterable[BlockerScore], improvement: float = 5.0) -> List[BlockerScore]:
    recovered: List[BlockerScore] = []
    for score in scores:
        boosted = min(100.0, score.score + improvement)
        recovered.append(BlockerScore(score.learner_id, round(boosted, 2), _band(boosted), list(score.blockers)))
    return recovered


def blocker_forecast(scores: Iterable[BlockerScore], weeks: int = 4) -> Dict[int, Dict[str, int]]:
    projection: Dict[int, Dict[str, int]] = {}
    current = list(scores)
    for week in range(1, max(1, weeks) + 1):
        current = simulate_recovery(current, improvement=2.5)
        projection[week] = blocker_summary(current)
    return projection
