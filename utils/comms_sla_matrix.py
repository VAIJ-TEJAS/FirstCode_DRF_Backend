"""Communication SLA matrix helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CommunicationEvent:
    channel: str
    response_minutes: int
    escalated: bool
    resolved: bool


@dataclass(frozen=True)
class CommsSLA:
    total_events: int
    median_response_minutes: float
    escalation_rate: float
    resolution_rate: float
    channel_mix: Dict[str, int]


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def build_sla_matrix(events: Iterable[CommunicationEvent]) -> CommsSLA:
    rows = list(events)
    if not rows:
        return CommsSLA(0, 0.0, 0.0, 0.0, {})

    escalations = len([row for row in rows if row.escalated])
    resolved = len([row for row in rows if row.resolved])
    response_times = sorted([max(0, row.response_minutes) for row in rows])
    mid = len(response_times) // 2
    median = response_times[mid] if response_times else 0

    channel_mix: Dict[str, int] = {}
    for row in rows:
        channel_mix[row.channel] = channel_mix.get(row.channel, 0) + 1

    return CommsSLA(
        total_events=len(rows),
        median_response_minutes=float(median),
        escalation_rate=_rate(escalations, len(rows)),
        resolution_rate=_rate(resolved, len(rows)),
        channel_mix=channel_mix,
    )


def channel_priority(events: Iterable[CommunicationEvent]) -> List[str]:
    mix = build_sla_matrix(events).channel_mix
    return [channel for channel, _ in sorted(mix.items(), key=lambda item: (-item[1], item[0]))]


def sla_digest(events: Iterable[CommunicationEvent]) -> Dict[str, object]:
    matrix = build_sla_matrix(events)
    return {
        "total_events": matrix.total_events,
        "median_response_minutes": matrix.median_response_minutes,
        "escalation_rate": matrix.escalation_rate,
        "resolution_rate": matrix.resolution_rate,
        "channel_mix": matrix.channel_mix,
        "channel_priority": channel_priority(events),
    }


def response_buckets(events: Iterable[CommunicationEvent]) -> Dict[str, int]:
    buckets = {"under_60": 0, "under_180": 0, "over_180": 0}
    for row in events:
        if row.response_minutes <= 60:
            buckets["under_60"] += 1
        elif row.response_minutes <= 180:
            buckets["under_180"] += 1
        else:
            buckets["over_180"] += 1
    return buckets


def escalation_pressure(events: Iterable[CommunicationEvent]) -> float:
    rows = list(events)
    if not rows:
        return 0.0
    escalations = len([row for row in rows if row.escalated])
    return _rate(escalations, len(rows))


def channel_digest(events: Iterable[CommunicationEvent]) -> Dict[str, object]:
    return {
        "channel_priority": channel_priority(events),
        "response_buckets": response_buckets(events),
        "escalation_pressure": escalation_pressure(events),
    }


def sla_targets(events: Iterable[CommunicationEvent], target_minutes: int = 120) -> Dict[str, object]:
    rows = list(events)
    if not rows:
        return {"target_minutes": target_minutes, "on_time_rate": 0.0}

    on_time = len([row for row in rows if row.response_minutes <= target_minutes])
    return {
        "target_minutes": target_minutes,
        "on_time_rate": _rate(on_time, len(rows)),
    }


def sla_forecast(events: Iterable[CommunicationEvent], weeks: int = 4) -> Dict[int, float]:
    rows = list(events)
    base = build_sla_matrix(rows).median_response_minutes if rows else 0.0
    return {week: round(max(0.0, base - week * 3.5), 2) for week in range(1, max(1, weeks) + 1)}


def escalation_watchlist(events: Iterable[CommunicationEvent], threshold_rate: float = 20.0) -> bool:
    return escalation_pressure(events) >= threshold_rate


def sla_score(events: Iterable[CommunicationEvent]) -> float:
    matrix = build_sla_matrix(events)
    if matrix.total_events == 0:
        return 100.0
    score = 100.0 - matrix.escalation_rate - (matrix.median_response_minutes / 10.0)
    return round(max(0.0, score), 2)
