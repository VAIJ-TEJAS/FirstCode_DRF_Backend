"""Guardian escalation matrix helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class GuardianEvent:
    learner_id: str
    channel: str
    status: str
    response_minutes: int
    escalated: bool


@dataclass(frozen=True)
class GuardianMatrix:
    total_events: int
    escalation_rate: float
    median_response_minutes: float
    channel_mix: Dict[str, int]


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def build_matrix(events: Iterable[GuardianEvent]) -> GuardianMatrix:
    rows = list(events)
    if not rows:
        return GuardianMatrix(0, 0.0, 0.0, {})

    escalations = len([row for row in rows if row.escalated])
    response_times = sorted([max(0, row.response_minutes) for row in rows])
    mid = len(response_times) // 2
    median = response_times[mid] if response_times else 0
    channel_mix: Dict[str, int] = {}

    for row in rows:
        channel_mix[row.channel] = (channel_mix.get(row.channel, 0) + 1)

    return GuardianMatrix(
        total_events=len(rows),
        escalation_rate=_rate(escalations, len(rows)),
        median_response_minutes=float(median),
        channel_mix=channel_mix,
    )


def watchlist(events: Iterable[GuardianEvent], threshold_minutes: int = 180) -> List[str]:
    risk: Dict[str, int] = {}
    for row in events:
        if row.escalated or row.response_minutes > threshold_minutes:
            risk[row.learner_id] = risk.get(row.learner_id, 0) + 1
    return [learner_id for learner_id, _ in sorted(risk.items(), key=lambda item: (-item[1], item[0]))]


def status_counts(events: Iterable[GuardianEvent]) -> Dict[str, int]:
    summary: Dict[str, int] = {}
    for row in events:
        summary[row.status] = summary.get(row.status, 0) + 1
    return summary


def escalation_digest(events: Iterable[GuardianEvent]) -> Dict[str, object]:
    rows = list(events)
    matrix = build_matrix(rows)
    return {
        "total_events": matrix.total_events,
        "escalation_rate": matrix.escalation_rate,
        "median_response_minutes": matrix.median_response_minutes,
        "channel_mix": matrix.channel_mix,
        "status_counts": status_counts(rows),
        "watchlist": watchlist(rows),
    }


def escalation_pressure(events: Iterable[GuardianEvent]) -> float:
    rows = list(events)
    if not rows:
        return 0.0
    escalations = len([row for row in rows if row.escalated])
    return round((escalations / len(rows)) * 100.0, 2)


def channel_priority(events: Iterable[GuardianEvent]) -> List[str]:
    mix = build_matrix(events).channel_mix
    return [channel for channel, _ in sorted(mix.items(), key=lambda item: (-item[1], item[0]))]


def response_buckets(events: Iterable[GuardianEvent]) -> Dict[str, int]:
    buckets = {"under_60": 0, "under_180": 0, "over_180": 0}
    for row in events:
        if row.response_minutes <= 60:
            buckets["under_60"] += 1
        elif row.response_minutes <= 180:
            buckets["under_180"] += 1
        else:
            buckets["over_180"] += 1
    return buckets


def guardian_digest(events: Iterable[GuardianEvent]) -> Dict[str, object]:
    rows = list(events)
    return {
        "total_events": len(rows),
        "escalation_rate": escalation_pressure(rows),
        "response_buckets": response_buckets(rows),
        "channel_priority": channel_priority(rows),
    }
