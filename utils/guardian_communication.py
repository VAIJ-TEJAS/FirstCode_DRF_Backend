"""Guardian communication digest helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class GuardianTouchpoint:
    learner_id: str
    channel: str
    outcome: str
    response_minutes: int
    escalation: bool


@dataclass(frozen=True)
class GuardianDigest:
    total_touchpoints: int
    success_rate: float
    escalation_rate: float
    median_response_minutes: float
    channel_mix: Dict[str, int]


def _rate(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((count / total) * 100.0, 2)


def build_digest(items: Iterable[GuardianTouchpoint]) -> GuardianDigest:
    rows = list(items)
    total = len(rows)

    if total == 0:
        return GuardianDigest(0, 0.0, 0.0, 0.0, {})

    success = 0
    escalations = 0
    response = []
    channel_mix: Dict[str, int] = {}

    for item in rows:
        if item.outcome.lower() in {"delivered", "acknowledged", "resolved"}:
            success += 1
        if item.escalation:
            escalations += 1
        response.append(max(0, item.response_minutes))
        channel_mix[item.channel] = channel_mix.get(item.channel, 0) + 1

    response.sort()
    middle = total // 2
    if total % 2 == 1:
        median = float(response[middle])
    else:
        median = round((response[middle - 1] + response[middle]) / 2.0, 2)

    return GuardianDigest(
        total_touchpoints=total,
        success_rate=_rate(success, total),
        escalation_rate=_rate(escalations, total),
        median_response_minutes=median,
        channel_mix=channel_mix,
    )


def risk_learners(items: Iterable[GuardianTouchpoint], response_threshold: int = 180) -> List[str]:
    risk: Dict[str, int] = {}
    for item in items:
        if item.escalation or item.response_minutes > response_threshold:
            risk[item.learner_id] = risk.get(item.learner_id, 0) + 1
    return [learner_id for learner_id, count in sorted(risk.items(), key=lambda row: (-row[1], row[0])) if count > 0]
