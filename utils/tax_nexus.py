from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class NexusSignal:
    jurisdiction: str
    annual_revenue: float
    transactions: int
    threshold_revenue: float
    threshold_transactions: int


@dataclass(frozen=True)
class NexusSummary:
    jurisdiction: str
    nexus: bool
    risk_score: int


def evaluate_nexus(signals: Iterable[NexusSignal]) -> List[NexusSummary]:
    summaries: List[NexusSummary] = []
    for signal in signals:
        revenue_ratio = signal.annual_revenue / signal.threshold_revenue if signal.threshold_revenue else 0
        transaction_ratio = signal.transactions / signal.threshold_transactions if signal.threshold_transactions else 0
        nexus = revenue_ratio >= 1 or transaction_ratio >= 1
        score = min(100, max(0, round(((revenue_ratio + transaction_ratio) / 2) * 100)))
        summaries.append(NexusSummary(signal.jurisdiction, nexus, score))
    return summaries
