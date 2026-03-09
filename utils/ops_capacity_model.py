"""Operational capacity model for cross-functional staffing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CapacityInput:
    team: str
    headcount: int
    avg_throughput_per_person: int
    incoming_work_items: int
    sla_target_hours: int


@dataclass(frozen=True)
class CapacityOutput:
    team: str
    capacity: int
    utilization_percent: float
    sla_risk: str


def _percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def evaluate_capacity(row: CapacityInput) -> CapacityOutput:
    capacity = max(0, row.headcount) * max(0, row.avg_throughput_per_person)
    utilization = _percent(max(0, row.incoming_work_items), max(1, capacity))

    risk = "low"
    if utilization >= 85 or row.sla_target_hours <= 12:
        risk = "medium"
    if utilization >= 100 or row.sla_target_hours <= 6:
        risk = "high"

    return CapacityOutput(team=row.team, capacity=capacity, utilization_percent=utilization, sla_risk=risk)


def portfolio_capacity(rows: Iterable[CapacityInput]) -> Dict[str, float]:
    outputs = [evaluate_capacity(row) for row in rows]
    if not outputs:
        return {"avg_utilization": 0.0, "high_risk_teams": 0.0}

    avg_util = round(sum(item.utilization_percent for item in outputs) / len(outputs), 2)
    high = len([item for item in outputs if item.sla_risk == "high"])

    return {
        "avg_utilization": avg_util,
        "high_risk_teams": float(high),
    }


def high_risk_teams(rows: Iterable[CapacityInput]) -> List[str]:
    return [item.team for item in rows if evaluate_capacity(item).sla_risk == "high"]


def detailed_capacity(rows: Iterable[CapacityInput]) -> Dict[str, Dict[str, float]]:
    details: Dict[str, Dict[str, float]] = {}
    for row in rows:
        output = evaluate_capacity(row)
        details[row.team] = {
            "capacity": float(output.capacity),
            "utilization_percent": output.utilization_percent,
            "sla_risk_score": 90.0 if output.sla_risk == "high" else 60.0 if output.sla_risk == "medium" else 20.0,
        }
    return details


def recommended_hiring(rows: Iterable[CapacityInput]) -> Dict[str, int]:
    recommendations: Dict[str, int] = {}
    for row in rows:
        output = evaluate_capacity(row)
        if output.sla_risk != "high":
            continue
        deficit = max(0, row.incoming_work_items - output.capacity)
        per_person = max(1, row.avg_throughput_per_person)
        recommendations[row.team] = int((deficit + per_person - 1) // per_person)
    return recommendations
