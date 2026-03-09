"""Proctoring capacity evaluators for large exam windows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ProctorShift:
    shift_id: str
    region: str
    proctor_count: int
    active_sessions: int
    queued_sessions: int


@dataclass(frozen=True)
class CapacitySignal:
    shift_id: str
    load_percent: float
    queue_percent: float
    status: str
    recommendation: str


def _percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def evaluate_shift(shift: ProctorShift) -> CapacitySignal:
    max_sessions = max(1, shift.proctor_count * 6)
    load_percent = _percent(max(0, shift.active_sessions), max_sessions)
    queue_percent = _percent(max(0, shift.queued_sessions), max_sessions)

    status = "stable"
    recommendation = "No action required"

    if load_percent >= 80 or queue_percent >= 10:
        status = "watch"
        recommendation = "Open standby proctor pool"

    if load_percent >= 95 or queue_percent >= 25:
        status = "critical"
        recommendation = "Trigger incident bridge and reroute sessions"

    return CapacitySignal(
        shift_id=shift.shift_id,
        load_percent=load_percent,
        queue_percent=queue_percent,
        status=status,
        recommendation=recommendation,
    )


def summarize_region(shifts: Iterable[ProctorShift]) -> Dict[str, float]:
    totals: Dict[str, Dict[str, int]] = {}

    for shift in shifts:
        if shift.region not in totals:
            totals[shift.region] = {"capacity": 0, "active": 0}
        totals[shift.region]["capacity"] += max(1, shift.proctor_count * 6)
        totals[shift.region]["active"] += max(0, shift.active_sessions)

    return {
        region: _percent(values["active"], values["capacity"])
        for region, values in totals.items()
    }


def intervention_queue(shifts: Iterable[ProctorShift]) -> List[CapacitySignal]:
    signals = [evaluate_shift(shift) for shift in shifts]
    ranked = sorted(signals, key=lambda item: (item.status != "critical", -item.queue_percent))
    return [item for item in ranked if item.status != "stable"]
