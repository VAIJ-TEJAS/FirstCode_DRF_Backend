from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class EscalationLoad:
    owner: str
    open_cases: int
    avg_age_hours: int


def load_pressure(loads: Iterable[EscalationLoad]) -> dict:
    loads_list = list(loads)
    if not loads_list:
        return {"total_cases": 0, "pressure": "low"}

    total_cases = sum(load.open_cases for load in loads_list)
    avg_age = sum(load.avg_age_hours for load in loads_list) / len(loads_list)

    if total_cases > 25 or avg_age > 48:
        pressure = "high"
    elif total_cases > 12 or avg_age > 24:
        pressure = "medium"
    else:
        pressure = "low"

    return {"total_cases": total_cases, "pressure": pressure}
