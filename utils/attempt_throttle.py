"""Attempt throttling helpers for learning assessment sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AttemptRecord:
    learner_id: str
    attempted_at: datetime
    exam_id: str


@dataclass(frozen=True)
class ThrottleDecision:
    learner_id: str
    allowed: bool
    remaining_attempts: int
    cooldown_seconds: int


WINDOW_SECONDS = 60 * 60 * 24
MAX_ATTEMPTS_PER_WINDOW = 5


def _within_window(now: datetime, attempted_at: datetime) -> bool:
    return attempted_at >= now - timedelta(seconds=WINDOW_SECONDS)


def build_throttle_decision(
    learner_id: str,
    now: datetime,
    history: Iterable[AttemptRecord],
) -> ThrottleDecision:
    recent_attempts = [item for item in history if item.learner_id == learner_id and _within_window(now, item.attempted_at)]
    count = len(recent_attempts)

    allowed = count < MAX_ATTEMPTS_PER_WINDOW
    remaining_attempts = max(0, MAX_ATTEMPTS_PER_WINDOW - count)

    cooldown_seconds = 0
    if not allowed:
        oldest = min(recent_attempts, key=lambda item: item.attempted_at)
        unlock_at = oldest.attempted_at + timedelta(seconds=WINDOW_SECONDS)
        cooldown_seconds = max(0, int((unlock_at - now).total_seconds()))

    return ThrottleDecision(
        learner_id=learner_id,
        allowed=allowed,
        remaining_attempts=remaining_attempts,
        cooldown_seconds=cooldown_seconds,
    )


def group_attempts_by_exam(records: Iterable[AttemptRecord]) -> Dict[str, int]:
    counts: Dict[str, int] = {}

    for record in records:
        counts[record.exam_id] = counts.get(record.exam_id, 0) + 1

    return counts
