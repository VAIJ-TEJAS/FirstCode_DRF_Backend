"""SLA forecasting helpers for support and review workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SlaBacklogPoint:
    queue: str
    open_items: int
    avg_handle_minutes: int
    agents_available: int


@dataclass(frozen=True)
class SlaForecast:
    queue: str
    estimated_clear_minutes: int
    estimated_breach_risk: str


def _risk(clear_minutes: int) -> str:
    if clear_minutes >= 24 * 60:
        return "critical"
    if clear_minutes >= 12 * 60:
        return "high"
    if clear_minutes >= 4 * 60:
        return "medium"
    return "low"


def build_sla_forecast(points: Iterable[SlaBacklogPoint]) -> List[SlaForecast]:
    forecasts: List[SlaForecast] = []

    for point in points:
        capacity_per_minute = max(1, point.agents_available)
        clear_minutes = int(round((point.open_items * max(1, point.avg_handle_minutes)) / capacity_per_minute))

        forecasts.append(
            SlaForecast(
                queue=point.queue,
                estimated_clear_minutes=clear_minutes,
                estimated_breach_risk=_risk(clear_minutes),
            )
        )

    return sorted(forecasts, key=lambda item: (-item.estimated_clear_minutes, item.queue))


def forecast_summary(items: Iterable[SlaForecast]) -> Dict[str, int]:
    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for item in items:
        summary[item.estimated_breach_risk] = summary.get(item.estimated_breach_risk, 0) + 1

    return summary
