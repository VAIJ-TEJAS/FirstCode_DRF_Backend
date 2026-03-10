from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class StaffingSignal:
    team: str
    required_fte: float
    available_fte: float


def staffing_envelope(signal: StaffingSignal) -> dict:
    gap = round(signal.required_fte - signal.available_fte, 2)
    if gap > 5:
        risk_band = "high"
    elif gap > 2:
        risk_band = "medium"
    else:
        risk_band = "low"

    return {"team": signal.team, "gap": gap, "risk_band": risk_band}


def staffing_summary(signals: Iterable[StaffingSignal]) -> list[dict]:
    return [staffing_envelope(signal) for signal in signals]
