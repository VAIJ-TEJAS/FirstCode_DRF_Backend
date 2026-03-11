"""Learner signal board aggregation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from utils.learning_blockers import BlockerScore, blocker_registry, blocker_summary


@dataclass(frozen=True)
class SignalBoard:
    cohort_id: str
    average_score: float
    band_summary: Dict[str, int]
    blocker_registry: Dict[str, List[str]]


def build_signal_board(cohort_id: str, scores: Iterable[BlockerScore]) -> SignalBoard:
    rows = list(scores)
    if not rows:
        return SignalBoard(cohort_id, 0.0, {"stable": 0, "watch": 0, "at_risk": 0, "critical": 0}, {})

    average_score = round(sum(score.score for score in rows) / len(rows), 2)

    return SignalBoard(
        cohort_id=cohort_id,
        average_score=average_score,
        band_summary=blocker_summary(rows),
        blocker_registry=blocker_registry(rows),
    )


def board_digest(cohort_id: str, scores: Iterable[BlockerScore]) -> Dict[str, object]:
    board = build_signal_board(cohort_id, scores)
    return {
        "cohort_id": board.cohort_id,
        "average_score": board.average_score,
        "band_summary": board.band_summary,
        "blocker_registry": board.blocker_registry,
    }


def board_alerts(cohort_id: str, scores: Iterable[BlockerScore]) -> Dict[str, object]:
    rows = list(scores)
    if not rows:
        return {"cohort_id": cohort_id, "alerts": []}
    critical = [score.learner_id for score in rows if score.band == "critical"]
    at_risk = [score.learner_id for score in rows if score.band == "at_risk"]
    return {"cohort_id": cohort_id, "alerts": critical + at_risk}


def board_trend(cohort_id: str, snapshots: List[List[BlockerScore]]) -> Dict[str, object]:
    if not snapshots:
        return {"cohort_id": cohort_id, "trend": []}

    trend = []
    for idx, rows in enumerate(snapshots, start=1):
        average = round(sum(score.score for score in rows) / len(rows), 2) if rows else 0.0
        trend.append({"week": idx, "average_score": average})

    return {"cohort_id": cohort_id, "trend": trend}


def board_heatmap(cohort_id: str, scores: Iterable[BlockerScore]) -> Dict[str, object]:
    rows = list(scores)
    if not rows:
        return {"cohort_id": cohort_id, "scores": {}}
    return {"cohort_id": cohort_id, "scores": {score.learner_id: score.score for score in rows}}


def board_digest_v2(cohort_id: str, scores: Iterable[BlockerScore]) -> Dict[str, object]:
    board = build_signal_board(cohort_id, scores)
    return {
        "cohort_id": board.cohort_id,
        "average_score": board.average_score,
        "band_summary": board.band_summary,
        "blocker_registry": board.blocker_registry,
        "alerts": board_alerts(cohort_id, scores),
        "heatmap": board_heatmap(cohort_id, scores),
    }


def board_confidence(scores: Iterable[BlockerScore]) -> str:
    rows = list(scores)
    if len(rows) < 10:
        return "low"
    avg = sum(score.score for score in rows) / len(rows)
    return "high" if avg >= 70 else "medium"
