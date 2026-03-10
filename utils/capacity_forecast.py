from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CapacitySignal:
    week: str
    seats: int
    utilization: float


def forecast_capacity(signals: Iterable[CapacitySignal]) -> dict:
    signals_list = list(signals)
    if not signals_list:
        return {"available_seats": 0, "utilization_rate": 0, "risk_band": "low"}

    total_seats = sum(max(signal.seats, 0) for signal in signals_list)
    avg_utilization = sum(max(signal.utilization, 0) for signal in signals_list) / len(signals_list)
    available_seats = round(total_seats / len(signals_list), 2)
    utilization_rate = round(avg_utilization, 2)

    if utilization_rate >= 0.9:
        risk_band = "high"
    elif utilization_rate >= 0.75:
        risk_band = "medium"
    else:
        risk_band = "low"

    return {
        "available_seats": available_seats,
        "utilization_rate": utilization_rate,
        "risk_band": risk_band,
    }
