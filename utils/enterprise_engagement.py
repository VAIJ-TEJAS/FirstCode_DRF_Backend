"""Enterprise engagement modeling helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class EngagementSignal:
    learner_id: str
    attendance_rate: float
    mentor_response_hours: float
    assessment_avg: float
    late_submissions: int


@dataclass(frozen=True)
class EngagementScore:
    learner_id: str
    score: float
    band: str
    interventions: List[str]


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


def evaluate_engagement(signal: EngagementSignal) -> EngagementScore:
    score = _clamp(
        signal.attendance_rate * 0.35
        + signal.assessment_avg * 0.35
        + (100.0 - signal.mentor_response_hours) * 0.2
        + max(0.0, 100.0 - signal.late_submissions * 4.0) * 0.1
    )

    interventions: List[str] = []
    if signal.attendance_rate < 75:
        interventions.append("attendance-recovery")
    if signal.assessment_avg < 60:
        interventions.append("concept-remediation")
    if signal.mentor_response_hours > 48:
        interventions.append("mentor-escalation")
    if signal.late_submissions > 3:
        interventions.append("late-submission-plan")

    return EngagementScore(signal.learner_id, round(score, 2), _band(score), interventions)


def engagement_summary(scores: Iterable[EngagementScore]) -> Dict[str, int]:
    summary = {"stable": 0, "watch": 0, "at_risk": 0, "critical": 0}
    for score in scores:
        summary[score.band] += 1
    return summary


def intervention_load(scores: Iterable[EngagementScore]) -> Dict[str, int]:
    load: Dict[str, int] = {}
    for score in scores:
        for intervention in score.interventions:
            load[intervention] = load.get(intervention, 0) + 1
    return load


def engagement_priority(scores: Iterable[EngagementScore], limit: int = 5) -> List[EngagementScore]:
    ranked = sorted(
        list(scores),
        key=lambda item: (
            0 if item.band == "critical" else 1 if item.band == "at_risk" else 2 if item.band == "watch" else 3,
            item.score,
        ),
    )
    return ranked[: max(0, limit)]


def engagement_heatmap(scores: Iterable[EngagementScore]) -> Dict[str, float]:
    return {score.learner_id: score.score for score in scores}


def engagement_digest(scores: Iterable[EngagementScore]) -> Dict[str, object]:
    rows = list(scores)
    if not rows:
        return {
            "total": 0,
            "average_score": 0.0,
            "band_summary": {"stable": 0, "watch": 0, "at_risk": 0, "critical": 0},
            "intervention_load": {},
        }

    avg_score = round(sum(item.score for item in rows) / len(rows), 2)
    return {
        "total": len(rows),
        "average_score": avg_score,
        "band_summary": engagement_summary(rows),
        "intervention_load": intervention_load(rows),
        "priority": [item.learner_id for item in engagement_priority(rows)],
    }


def cohort_velocity(scores: Iterable[EngagementScore], weeks: List[int]) -> Dict[int, float]:
    rows = list(scores)
    if not rows:
        return {week: 0.0 for week in weeks}

    base = round(sum(item.score for item in rows) / len(rows), 2)
    return {week: round(max(0.0, base - (week - 1) * 0.4), 2) for week in weeks}


def risk_registry(scores: Iterable[EngagementScore]) -> Dict[str, List[str]]:
    registry = {"at_risk": [], "critical": []}
    for score in scores:
        if score.band == "at_risk":
            registry["at_risk"].append(score.learner_id)
        if score.band == "critical":
            registry["critical"].append(score.learner_id)
    return registry


def target_interventions(scores: Iterable[EngagementScore]) -> Dict[str, List[str]]:
    targets: Dict[str, List[str]] = {}
    for score in scores:
        for intervention in score.interventions:
            targets.setdefault(intervention, []).append(score.learner_id)
    return targets


def simulate_recovery(scores: Iterable[EngagementScore], improvement: float = 5.0) -> List[EngagementScore]:
    recovered: List[EngagementScore] = []
    for score in scores:
        boosted = min(100.0, score.score + improvement)
        recovered.append(
            EngagementScore(
                learner_id=score.learner_id,
                score=round(boosted, 2),
                band=_band(boosted),
                interventions=list(score.interventions),
            )
        )
    return recovered


def recovery_projection(scores: Iterable[EngagementScore], weeks: int = 4) -> Dict[int, Dict[str, int]]:
    projection: Dict[int, Dict[str, int]] = {}
    current = list(scores)
    for week in range(1, max(1, weeks) + 1):
        current = simulate_recovery(current, improvement=2.5)
        projection[week] = engagement_summary(current)
    return projection
