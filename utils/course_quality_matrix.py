"""Course quality matrix helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CourseQualitySignal:
    course_id: str
    completion_rate: float
    assessment_avg: float
    nps_score: float
    instructor_rating: float


@dataclass(frozen=True)
class CourseQualityScore:
    course_id: str
    score: float
    tier: str
    actions: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _tier(score: float) -> str:
    if score >= 85:
        return "excellent"
    if score >= 70:
        return "good"
    if score >= 55:
        return "watch"
    return "critical"


def evaluate_quality(signal: CourseQualitySignal) -> CourseQualityScore:
    score = _clamp(
        signal.completion_rate * 0.35
        + signal.assessment_avg * 0.30
        + signal.nps_score * 0.20
        + signal.instructor_rating * 0.15
    )

    tier = _tier(score)
    actions: List[str] = []
    if tier == "watch":
        actions.append("launch-quality-review")
    if tier == "critical":
        actions.append("pause-new-intake")
        actions.append("assign-remediation-squad")

    return CourseQualityScore(signal.course_id, round(score, 2), tier, actions)


def quality_summary(scores: Iterable[CourseQualityScore]) -> Dict[str, int]:
    summary = {"excellent": 0, "good": 0, "watch": 0, "critical": 0}
    for score in scores:
        summary[score.tier] += 1
    return summary


def quality_digest(signals: Iterable[CourseQualitySignal]) -> Dict[str, object]:
    scores = [evaluate_quality(signal) for signal in signals]
    if not scores:
        return {"average_score": 0.0, "summary": quality_summary([]), "actions": []}

    avg_score = round(sum(score.score for score in scores) / len(scores), 2)
    actions = [action for score in scores for action in score.actions]

    return {
        "average_score": avg_score,
        "summary": quality_summary(scores),
        "actions": actions,
    }


def quality_rankings(signals: Iterable[CourseQualitySignal]) -> List[CourseQualityScore]:
    return sorted([evaluate_quality(signal) for signal in signals], key=lambda item: item.score, reverse=True)


def quality_heatmap(signals: Iterable[CourseQualitySignal]) -> Dict[str, float]:
    return {signal.course_id: evaluate_quality(signal).score for signal in signals}


def quality_forecast(signals: Iterable[CourseQualitySignal], weeks: int = 4) -> Dict[int, float]:
    scores = [evaluate_quality(signal).score for signal in signals]
    base = round(sum(scores) / len(scores), 2) if scores else 0.0
    return {week: round(max(0.0, base - (week - 1) * 0.6), 2) for week in range(1, max(1, weeks) + 1)}


def risk_registry(signals: Iterable[CourseQualitySignal]) -> Dict[str, List[str]]:
    registry = {"watch": [], "critical": []}
    for signal in signals:
        score = evaluate_quality(signal)
        if score.tier in registry:
            registry[score.tier].append(score.course_id)
    return registry


def action_map(signals: Iterable[CourseQualitySignal]) -> Dict[str, List[str]]:
    return {signal.course_id: evaluate_quality(signal).actions for signal in signals}


def quality_board(signals: Iterable[CourseQualitySignal]) -> Dict[str, object]:
    scores = [evaluate_quality(signal) for signal in signals]
    if not scores:
        return {"average_score": 0.0, "summary": quality_summary([]), "actions": {}, "risk_registry": {}}
    avg_score = round(sum(score.score for score in scores) / len(scores), 2)
    return {
        "average_score": avg_score,
        "summary": quality_summary(scores),
        "actions": action_map(signals),
        "risk_registry": risk_registry(signals),
    }


def quality_variance(signals: Iterable[CourseQualitySignal]) -> float:
    scores = [evaluate_quality(signal).score for signal in signals]
    if len(scores) < 2:
        return 0.0
    return round(max(scores) - min(scores), 2)


def quality_confidence(signals: Iterable[CourseQualitySignal]) -> str:
    variance = quality_variance(signals)
    count = len(list(signals))
    if count < 5:
        return "low"
    if variance > 20:
        return "medium"
    return "high"


def quality_alerts(signals: Iterable[CourseQualitySignal]) -> List[str]:
    alerts: List[str] = []
    for signal in signals:
        score = evaluate_quality(signal)
        if score.tier in {"watch", "critical"}:
            alerts.append(score.course_id)
    return alerts
