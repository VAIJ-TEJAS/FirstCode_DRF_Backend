"""Lesson health board utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class LessonHealth:
    lesson_id: str
    drop_rate: float
    engagement_rate: float
    quiz_avg: float


@dataclass(frozen=True)
class LessonScore:
    lesson_id: str
    score: float
    tier: str


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_lesson(lesson: LessonHealth) -> LessonScore:
    score = _clamp(
        (100.0 - lesson.drop_rate) * 0.35
        + lesson.engagement_rate * 0.35
        + lesson.quiz_avg * 0.30
    )

    tier = "healthy"
    if score < 70:
        tier = "watch"
    if score < 55:
        tier = "critical"

    return LessonScore(lesson.lesson_id, round(score, 2), tier)


def lesson_digest(lessons: Iterable[LessonHealth]) -> Dict[str, object]:
    scores = [evaluate_lesson(lesson) for lesson in lessons]
    if not scores:
        return {"average_score": 0.0, "watch": [], "critical": []}

    avg_score = round(sum(score.score for score in scores) / len(scores), 2)
    watch = [score.lesson_id for score in scores if score.tier == "watch"]
    critical = [score.lesson_id for score in scores if score.tier == "critical"]

    return {"average_score": avg_score, "watch": watch, "critical": critical}


def lesson_heatmap(lessons: Iterable[LessonHealth]) -> Dict[str, float]:
    return {lesson.lesson_id: evaluate_lesson(lesson).score for lesson in lessons}


def lesson_summary(lessons: Iterable[LessonHealth]) -> Dict[str, int]:
    summary = {"healthy": 0, "watch": 0, "critical": 0}
    for lesson in lessons:
        summary[evaluate_lesson(lesson).tier] += 1
    return summary


def lesson_trend(weekly_snapshots: List[List[LessonHealth]]) -> Dict[int, float]:
    trend: Dict[int, float] = {}
    for idx, snapshot in enumerate(weekly_snapshots, start=1):
        scores = [evaluate_lesson(lesson).score for lesson in snapshot]
        avg = round(sum(scores) / len(scores), 2) if scores else 0.0
        trend[idx] = avg
    return trend


def lesson_priority(lessons: Iterable[LessonHealth], limit: int = 5) -> List[str]:
    ranked = sorted(
        [evaluate_lesson(lesson) for lesson in lessons],
        key=lambda score: (0 if score.tier == "critical" else 1 if score.tier == "watch" else 2, score.score),
    )
    return [score.lesson_id for score in ranked[: max(0, limit)]]


def lesson_alerts(lessons: Iterable[LessonHealth]) -> List[str]:
    return [score.lesson_id for score in [evaluate_lesson(lesson) for lesson in lessons] if score.tier != "healthy"]
