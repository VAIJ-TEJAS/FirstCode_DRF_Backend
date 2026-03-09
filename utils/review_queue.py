"""Review queue prioritization for enterprise support workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ReviewTicket:
    ticket_id: str
    learner_id: str
    queue: str
    severity: str
    age_minutes: int


@dataclass(frozen=True)
class QueueSnapshot:
    ordered_ids: List[str]
    by_queue: Dict[str, int]
    oldest_age_minutes: int


SEVERITY_PRIORITY = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}


def _priority(ticket: ReviewTicket) -> int:
    return SEVERITY_PRIORITY.get(ticket.severity.lower(), 1)


def build_queue_snapshot(tickets: Iterable[ReviewTicket]) -> QueueSnapshot:
    items = list(tickets)

    ordered = sorted(
        items,
        key=lambda ticket: (
            -_priority(ticket),
            -max(0, ticket.age_minutes),
            ticket.ticket_id,
        ),
    )

    by_queue: Dict[str, int] = {}
    for ticket in items:
        by_queue[ticket.queue] = by_queue.get(ticket.queue, 0) + 1

    oldest = 0
    if items:
        oldest = max(max(0, ticket.age_minutes) for ticket in items)

    return QueueSnapshot(
        ordered_ids=[ticket.ticket_id for ticket in ordered],
        by_queue=by_queue,
        oldest_age_minutes=oldest,
    )
