"""Enterprise command center workflow helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CommandSignal:
    source: str
    severity: str
    message: str
    service: str


@dataclass(frozen=True)
class CommandCenterSnapshot:
    status: str
    signal_count: int
    highest_severity: str
    by_source: Dict[str, int]
    by_service: Dict[str, int]
    action_required: bool


SEVERITY_WEIGHT = {
    "info": 1,
    "warning": 2,
    "error": 3,
    "critical": 4,
}


def _normalize_severity(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in SEVERITY_WEIGHT:
        return normalized
    return "warning"


def _select_status(highest: str, total: int) -> str:
    if highest == "critical":
        return "blocked"
    if highest == "error":
        return "degraded"
    if highest == "warning" and total >= 5:
        return "watch"
    if total == 0:
        return "idle"
    return "healthy"


def build_command_center_snapshot(signals: Iterable[CommandSignal]) -> CommandCenterSnapshot:
    by_source: Dict[str, int] = {}
    by_service: Dict[str, int] = {}

    highest = "info"
    total = 0

    for signal in signals:
        total += 1
        severity = _normalize_severity(signal.severity)

        if SEVERITY_WEIGHT[severity] > SEVERITY_WEIGHT[highest]:
            highest = severity

        by_source[signal.source] = by_source.get(signal.source, 0) + 1
        by_service[signal.service] = by_service.get(signal.service, 0) + 1

    status = _select_status(highest, total)

    return CommandCenterSnapshot(
        status=status,
        signal_count=total,
        highest_severity=highest,
        by_source=by_source,
        by_service=by_service,
        action_required=status in {"blocked", "degraded", "watch"},
    )


def priority_sources(snapshot: CommandCenterSnapshot) -> List[str]:
    return [
        source
        for source, _ in sorted(snapshot.by_source.items(), key=lambda item: (-item[1], item[0]))
    ]
