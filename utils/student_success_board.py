"""Student success board aggregations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from utils.enterprise_engagement import EngagementScore, engagement_summary, intervention_load


@dataclass(frozen=True)
class SuccessBoard:
    cohort_id: str
    average_score: float
    band_summary: Dict[str, int]
    intervention_load: Dict[str, int]


def build_success_board(cohort_id: str, scores: Iterable[EngagementScore]) -> SuccessBoard:
    rows = list(scores)
    if not rows:
        return SuccessBoard(cohort_id, 0.0, {"stable": 0, "watch": 0, "at_risk": 0, "critical": 0}, {})

    average_score = round(sum(score.score for score in rows) / len(rows), 2)

    return SuccessBoard(
        cohort_id=cohort_id,
        average_score=average_score,
        band_summary=engagement_summary(rows),
        intervention_load=intervention_load(rows),
    )


def board_heatmap(cohort_id: str, scores: Iterable[EngagementScore]) -> Dict[str, object]:
    rows = list(scores)
    if not rows:
        return {"cohort_id": cohort_id, "scores": {}}
    return {
        "cohort_id": cohort_id,
        "scores": {score.learner_id: score.score for score in rows},
    }


def board_digest(cohort_id: str, scores: Iterable[EngagementScore]) -> Dict[str, object]:
    board = build_success_board(cohort_id, scores)
    return {
        "cohort_id": board.cohort_id,
        "average_score": board.average_score,
        "band_summary": board.band_summary,
        "intervention_load": board.intervention_load,
        "heatmap": board_heatmap(cohort_id, scores),
    }


def board_trend(cohort_id: str, snapshots: List[List[EngagementScore]]) -> Dict[str, object]:
    if not snapshots:
        return {"cohort_id": cohort_id, "trend": []}

    trend = []
    for idx, rows in enumerate(snapshots, start=1):
        average = round(sum(score.score for score in rows) / len(rows), 2) if rows else 0.0
        trend.append({"week": idx, "average_score": average})

    return {"cohort_id": cohort_id, "trend": trend}


def board_alerts(cohort_id: str, scores: Iterable[EngagementScore]) -> Dict[str, object]:
    rows = list(scores)
    if not rows:
        return {"cohort_id": cohort_id, "alerts": []}
    critical = [score.learner_id for score in rows if score.band == "critical"]
    at_risk = [score.learner_id for score in rows if score.band == "at_risk"]
    return {"cohort_id": cohort_id, "alerts": critical + at_risk}
