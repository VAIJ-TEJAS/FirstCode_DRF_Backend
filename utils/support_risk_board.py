"""Support risk board helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SupportSignal:
    learner_id: str
    tickets_open: int
    avg_response_hours: float
    escalations: int


@dataclass(frozen=True)
class SupportRisk:
    learner_id: str
    score: float
    tier: str


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_support(signal: SupportSignal) -> SupportRisk:
    score = _clamp(
        max(0, 100.0 - signal.tickets_open * 6.0)
        + max(0, 100.0 - signal.avg_response_hours * 2.0)
        - signal.escalations * 8.0
    )

    tier = "stable"
    if score < 70:
        tier = "watch"
    if score < 55:
        tier = "critical"

    return SupportRisk(signal.learner_id, round(score, 2), tier)


def risk_summary(signals: Iterable[SupportSignal]) -> Dict[str, int]:
    summary = {"stable": 0, "watch": 0, "critical": 0}
    for signal in signals:
        summary[evaluate_support(signal).tier] += 1
    return summary


def risk_heatmap(signals: Iterable[SupportSignal]) -> Dict[str, float]:
    return {signal.learner_id: evaluate_support(signal).score for signal in signals}


def support_digest(signals: Iterable[SupportSignal]) -> Dict[str, object]:
    scores = [evaluate_support(signal) for signal in signals]
    if not scores:
        return {"average_score": 0.0, "summary": risk_summary([]), "watchlist": []}

    avg_score = round(sum(score.score for score in scores) / len(scores), 2)
    watchlist = [score.learner_id for score in scores if score.tier != "stable"]

    return {"average_score": avg_score, "summary": risk_summary(signals), "watchlist": watchlist}


def escalation_map(signals: Iterable[SupportSignal], threshold: int = 2) -> List[str]:
    escalated: List[str] = []
    for signal in signals:
        if signal.escalations >= threshold:
            escalated.append(signal.learner_id)
    return escalated


def support_board(signals: Iterable[SupportSignal]) -> Dict[str, object]:
    return {
        "summary": risk_summary(signals),
        "escalations": escalation_map(signals),
        "heatmap": risk_heatmap(signals),
    }


def response_pressure(signals: Iterable[SupportSignal], threshold_hours: float = 24.0) -> List[str]:
    return [signal.learner_id for signal in signals if signal.avg_response_hours >= threshold_hours]


def ticket_heat(signals: Iterable[SupportSignal], threshold: int = 3) -> List[str]:
    return [signal.learner_id for signal in signals if signal.tickets_open >= threshold]


def support_pressure(signals: Iterable[SupportSignal]) -> float:
    scores = [evaluate_support(signal).score for signal in signals]
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 2)
