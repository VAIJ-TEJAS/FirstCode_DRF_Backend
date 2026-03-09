"""Parent portal engagement signals for learner support."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ParentPortalEvent:
    learner_id: str
    event_type: str
    response_minutes: int
    resolved: bool


@dataclass(frozen=True)
class ParentPortalSummary:
    learner_id: str
    events: int
    avg_response_minutes: float
    resolution_rate: float
    status: str


def _avg(values: List[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def summarize_learner(events: Iterable[ParentPortalEvent], learner_id: str) -> ParentPortalSummary:
    rows = [item for item in events if item.learner_id == learner_id]
    if not rows:
        return ParentPortalSummary(learner_id, 0, 0.0, 0.0, "stable")

    avg_response = _avg([max(0, item.response_minutes) for item in rows])
    resolved = len([item for item in rows if item.resolved])
    resolution_rate = round((resolved / len(rows)) * 100.0, 2)

    status = "stable"
    if avg_response > 180 or resolution_rate < 70:
        status = "watch"
    if avg_response > 360 or resolution_rate < 50:
        status = "critical"

    return ParentPortalSummary(
        learner_id=learner_id,
        events=len(rows),
        avg_response_minutes=avg_response,
        resolution_rate=resolution_rate,
        status=status,
    )


def watchlist(events: Iterable[ParentPortalEvent]) -> List[str]:
    learners = sorted({item.learner_id for item in events})
    return [learner for learner in learners if summarize_learner(events, learner).status != "stable"]


def status_counts(events: Iterable[ParentPortalEvent]) -> Dict[str, int]:
    summary = {"stable": 0, "watch": 0, "critical": 0}
    for learner in sorted({item.learner_id for item in events}):
        summary[summarize_learner(events, learner).status] += 1
    return summary


def portal_digest(events: Iterable[ParentPortalEvent]) -> Dict[str, object]:
    rows = list(events)
    learners = sorted({item.learner_id for item in rows})
    summaries = [summarize_learner(rows, learner) for learner in learners]
    return {
        "learner_count": len(learners),
        "status_counts": status_counts(rows),
        "watchlist": watchlist(rows),
        "average_response_minutes": round(
            sum(item.avg_response_minutes for item in summaries) / len(summaries), 2
        )
        if summaries
        else 0.0,
    }
