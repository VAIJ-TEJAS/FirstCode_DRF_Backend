from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CollectionsPoint:
    period: str
    recovered: float
    written_off: float


def forecast_recovery(points: Iterable[CollectionsPoint]) -> dict:
    recovered_total = sum(point.recovered for point in points)
    writeoff_total = sum(point.written_off for point in points)
    total = recovered_total + writeoff_total
    recovery_rate = round((recovered_total / total) * 100, 2) if total else 0.0
    return {
        "recovered_total": round(recovered_total, 2),
        "writeoff_total": round(writeoff_total, 2),
        "recovery_rate": recovery_rate,
    }


def recovery_trend(points: Iterable[CollectionsPoint]) -> str:
    points_list = list(points)
    if len(points_list) < 2:
        return "flat"
    last = points_list[-1].recovered
    prev = points_list[-2].recovered
    if last > prev * 1.1:
        return "accelerating"
    if last < prev * 0.9:
        return "slowing"
    return "flat"
