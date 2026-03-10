from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class AttendanceRecord:
    cohort_id: str
    sessions: int
    attended: int


def attendance_rollup(records: Iterable[AttendanceRecord]) -> dict:
    records_list = list(records)
    if not records_list:
        return {"attendance_rate": 0, "sessions": 0}

    total_sessions = sum(record.sessions for record in records_list)
    total_attended = sum(record.attended for record in records_list)
    rate = 0 if total_sessions == 0 else round(total_attended / total_sessions, 2)

    return {"attendance_rate": rate, "sessions": total_sessions}
