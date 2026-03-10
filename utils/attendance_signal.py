from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttendanceSignal:
    cohort_id: str
    sessions: int
    attended: int
    late_joins: int


def attendance_health(signal: AttendanceSignal) -> dict:
    if signal.sessions <= 0:
        attendance_rate = 0
    else:
        attendance_rate = round(signal.attended / signal.sessions, 2)

    late_penalty = min(signal.late_joins * 0.02, 0.3)
    reliability = round(max(attendance_rate - late_penalty, 0), 2)

    if reliability < 0.7:
        risk_band = "high"
    elif reliability < 0.85:
        risk_band = "medium"
    else:
        risk_band = "low"

    return {
        "cohort_id": signal.cohort_id,
        "attendance_rate": attendance_rate,
        "reliability": reliability,
        "risk_band": risk_band,
    }
