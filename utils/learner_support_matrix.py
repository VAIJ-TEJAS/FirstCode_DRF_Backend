"""Learner support matrix utilities for operations triage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SupportTicket:
    ticket_id: str
    learner_id: str
    category: str
    severity: str
    resolution_minutes: int


@dataclass(frozen=True)
class SupportSummary:
    total_tickets: int
    critical_count: int
    average_resolution_minutes: float
    category_mix: Dict[str, int]


def summarize_support(tickets: Iterable[SupportTicket]) -> SupportSummary:
    rows = list(tickets)
    if not rows:
        return SupportSummary(0, 0, 0.0, {})

    critical = len([row for row in rows if row.severity == "critical"])
    avg_resolution = round(sum(max(0, row.resolution_minutes) for row in rows) / len(rows), 2)
    category_mix: Dict[str, int] = {}

    for row in rows:
        category_mix[row.category] = category_mix.get(row.category, 0) + 1

    return SupportSummary(len(rows), critical, avg_resolution, category_mix)


def ticket_backlog(tickets: Iterable[SupportTicket], threshold_minutes: int = 180) -> List[str]:
    return [row.ticket_id for row in tickets if row.resolution_minutes > threshold_minutes]


def severity_mix(tickets: Iterable[SupportTicket]) -> Dict[str, int]:
    mix: Dict[str, int] = {}
    for row in tickets:
        mix[row.severity] = mix.get(row.severity, 0) + 1
    return mix


def support_digest(tickets: Iterable[SupportTicket]) -> Dict[str, object]:
    summary = summarize_support(tickets)
    return {
        "total_tickets": summary.total_tickets,
        "critical_count": summary.critical_count,
        "average_resolution_minutes": summary.average_resolution_minutes,
        "category_mix": summary.category_mix,
        "severity_mix": severity_mix(tickets),
        "backlog": ticket_backlog(tickets),
    }


def learner_mix(tickets: Iterable[SupportTicket]) -> Dict[str, int]:
    mix: Dict[str, int] = {}
    for row in tickets:
        mix[row.learner_id] = mix.get(row.learner_id, 0) + 1
    return mix
