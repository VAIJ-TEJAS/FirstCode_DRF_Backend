"""Curriculum release velocity helpers for content operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CurriculumCheckpoint:
    checkpoint_id: str
    track_id: str
    sprint: int
    planned_lessons: int
    delivered_lessons: int
    blocked_lessons: int


@dataclass(frozen=True)
class VelocitySummary:
    track_id: str
    delivery_rate: float
    block_rate: float
    momentum: str


def _percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def summarize_velocity(track_id: str, checkpoints: Iterable[CurriculumCheckpoint]) -> VelocitySummary:
    rows = [item for item in checkpoints if item.track_id == track_id]
    if not rows:
        return VelocitySummary(track_id=track_id, delivery_rate=0.0, block_rate=0.0, momentum="flat")

    planned = sum(max(0, item.planned_lessons) for item in rows)
    delivered = sum(max(0, item.delivered_lessons) for item in rows)
    blocked = sum(max(0, item.blocked_lessons) for item in rows)

    delivery_rate = _percent(delivered, planned if planned > 0 else 1)
    block_rate = _percent(blocked, planned if planned > 0 else 1)

    momentum = "flat"
    if delivery_rate >= 90 and block_rate <= 8:
        momentum = "accelerating"
    elif delivery_rate < 70 or block_rate > 15:
        momentum = "slowing"

    return VelocitySummary(track_id=track_id, delivery_rate=delivery_rate, block_rate=block_rate, momentum=momentum)


def sprint_breakdown(checkpoints: Iterable[CurriculumCheckpoint], track_id: str) -> Dict[int, Dict[str, float]]:
    rows = [item for item in checkpoints if item.track_id == track_id]
    result: Dict[int, Dict[str, float]] = {}

    for row in rows:
        planned = max(1, row.planned_lessons)
        result[row.sprint] = {
            "delivery_rate": _percent(row.delivered_lessons, planned),
            "block_rate": _percent(row.blocked_lessons, planned),
        }

    return dict(sorted(result.items(), key=lambda item: item[0]))
