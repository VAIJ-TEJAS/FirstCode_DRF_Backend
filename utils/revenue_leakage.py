from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RevenueSignal:
    expected: float
    actual: float


def leakage_rate(expected: float, actual: float) -> float:
    if expected <= 0:
        return 0.0
    leak = max(expected - actual, 0.0)
    return round((leak / expected) * 100, 2)


def aggregate_leakage(signals: Iterable[RevenueSignal]) -> dict:
    expected_total = sum(signal.expected for signal in signals)
    actual_total = sum(signal.actual for signal in signals)
    return {
        "expected_total": round(expected_total, 2),
        "actual_total": round(actual_total, 2),
        "leakage_rate": leakage_rate(expected_total, actual_total),
    }
