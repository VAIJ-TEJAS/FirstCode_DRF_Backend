from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HandoffMetric:
    owner: str
    handoffs: int
    avg_delay_hours: int


def handoff_metrics(metrics: Iterable[HandoffMetric]) -> dict:
    metrics_list = list(metrics)
    if not metrics_list:
        return {"handoffs": 0, "avg_delay": 0}

    total_handoffs = sum(metric.handoffs for metric in metrics_list)
    avg_delay = sum(metric.avg_delay_hours for metric in metrics_list) / len(metrics_list)

    return {"handoffs": total_handoffs, "avg_delay": round(avg_delay, 2)}
