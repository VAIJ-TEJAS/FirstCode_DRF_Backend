from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AdjustmentLine:
    invoice_id: str
    description: str
    amount: float


def apply_adjustments(base_amount: float, adjustments: Iterable[AdjustmentLine]) -> float:
    total_adjustment = sum(adjustment.amount for adjustment in adjustments)
    return round(base_amount + total_adjustment, 2)


def adjustment_summary(adjustments: Iterable[AdjustmentLine]) -> dict:
    count = 0
    total = 0.0
    for adjustment in adjustments:
        total += adjustment.amount
        count += 1
    return {
        "count": count,
        "total": round(total, 2),
    }
