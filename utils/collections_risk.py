from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class CollectionsSignal:
    invoice_id: str
    days_outstanding: int
    amount: float
    risk_score: int


@dataclass(frozen=True)
class CollectionsRisk:
    invoice_id: str
    priority: int
    band: str


def risk_band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def prioritize_collections(signals: Iterable[CollectionsSignal]) -> List[CollectionsRisk]:
    risks: List[CollectionsRisk] = []
    for signal in signals:
        priority = signal.days_outstanding * 2 + int(signal.amount // 1000)
        risks.append(CollectionsRisk(signal.invoice_id, priority, risk_band(signal.risk_score)))
    return sorted(risks, key=lambda item: item.priority, reverse=True)
