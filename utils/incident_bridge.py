"""Incident bridge utilities for release command center workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class IncidentSignal:
    source: str
    service: str
    severity: str
    message: str


@dataclass(frozen=True)
class IncidentBridgeSnapshot:
    highest_severity: str
    total_signals: int
    by_source: Dict[str, int]
    by_service: Dict[str, int]
    page_on_call: bool


SEVERITY_ORDER = {
    "info": 1,
    "warning": 2,
    "error": 3,
    "critical": 4,
}


def _normalize_severity(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in SEVERITY_ORDER:
        return normalized
    return "warning"


def _max_severity(left: str, right: str) -> str:
    if SEVERITY_ORDER[left] >= SEVERITY_ORDER[right]:
        return left
    return right


def build_incident_bridge_snapshot(signals: Iterable[IncidentSignal]) -> IncidentBridgeSnapshot:
    by_source: Dict[str, int] = {}
    by_service: Dict[str, int] = {}

    highest = "info"
    total = 0

    for signal in signals:
        total += 1

        severity = _normalize_severity(signal.severity)
        highest = _max_severity(highest, severity)

        by_source[signal.source] = by_source.get(signal.source, 0) + 1
        by_service[signal.service] = by_service.get(signal.service, 0) + 1

    page_on_call = highest in {"error", "critical"}

    return IncidentBridgeSnapshot(
        highest_severity=highest,
        total_signals=total,
        by_source=by_source,
        by_service=by_service,
        page_on_call=page_on_call,
    )


def merge_signals(primary: Iterable[IncidentSignal], secondary: Iterable[IncidentSignal]) -> List[IncidentSignal]:
    merged = [*primary, *secondary]

    return sorted(
        merged,
        key=lambda item: (
            -SEVERITY_ORDER[_normalize_severity(item.severity)],
            item.source,
            item.service,
            item.message,
        ),
    )
