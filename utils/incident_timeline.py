from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class IncidentEvent:
    incident_id: str
    timestamp: str
    owner: str
    severity: str


def _hours_between(start: str, end: str) -> int:
    delta = (parse_iso(end) - parse_iso(start)).total_seconds()
    return max(0, round(delta / 3600))


def parse_iso(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def build_incident_timeline(events: Iterable[IncidentEvent]) -> dict | None:
    events_list = list(events)
    if not events_list:
        return None

    events_sorted = sorted(events_list, key=lambda event: parse_iso(event.timestamp))
    first = events_sorted[0]
    last = events_sorted[-1]
    owners = sorted({event.owner for event in events_sorted})
    severity = "low"
    for event in events_sorted:
        if event.severity == "high":
            severity = "high"
        elif event.severity == "medium" and severity != "high":
            severity = "medium"

    return {
        "incident_id": first.incident_id,
        "first_seen": first.timestamp,
        "last_seen": last.timestamp,
        "owners": owners,
        "severity": severity,
        "elapsed_hours": _hours_between(first.timestamp, last.timestamp),
    }
