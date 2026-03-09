"""Learner completion forecast helpers for enterprise planning."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CompletionSnapshot:
    week: int
    active_learners: int
    completed_modules: int
    pending_modules: int
    dropped_learners: int


@dataclass(frozen=True)
class CompletionForecast:
    expected_completions: int
    completion_rate: float
    drop_rate: float
    confidence: str


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def forecast_completion(snapshots: Iterable[CompletionSnapshot]) -> CompletionForecast:
    rows = list(snapshots)
    if not rows:
        return CompletionForecast(0, 0.0, 0.0, "low")

    completion_rates = [_rate(item.completed_modules, max(1, item.completed_modules + item.pending_modules)) for item in rows]
    drop_rates = [_rate(item.dropped_learners, max(1, item.active_learners)) for item in rows]

    avg_completion = round(mean(completion_rates), 2)
    avg_drop = round(mean(drop_rates), 2)

    active = sum(max(0, item.active_learners) for item in rows)
    expected = int(round((active / max(1, len(rows))) * (avg_completion / 100.0) * (1 - (avg_drop / 100.0))))

    confidence = "high"
    if len(rows) < 3:
        confidence = "medium"
    if active < 120:
        confidence = "low"

    return CompletionForecast(
        expected_completions=max(0, expected),
        completion_rate=avg_completion,
        drop_rate=avg_drop,
        confidence=confidence,
    )


def week_completion_map(snapshots: Iterable[CompletionSnapshot]) -> Dict[int, float]:
    return {
        item.week: _rate(item.completed_modules, max(1, item.completed_modules + item.pending_modules))
        for item in sorted(list(snapshots), key=lambda row: row.week)
    }


def risk_weeks(snapshots: Iterable[CompletionSnapshot], completion_threshold: float = 65.0) -> List[int]:
    week_map = week_completion_map(snapshots)
    return [week for week, rate in week_map.items() if rate < completion_threshold]


def drop_pressure(snapshots: Iterable[CompletionSnapshot]) -> float:
    rows = list(snapshots)
    if not rows:
        return 0.0

    dropped = sum(max(0, item.dropped_learners) for item in rows)
    active = sum(max(0, item.active_learners) for item in rows)
    return _rate(dropped, max(1, active))


def projection_matrix(program_to_snapshots: Dict[str, List[CompletionSnapshot]]) -> Dict[str, Dict[str, object]]:
    matrix: Dict[str, Dict[str, object]] = {}
    for program_id, rows in sorted(program_to_snapshots.items(), key=lambda item: item[0]):
        forecast = forecast_completion(rows)
        matrix[program_id] = {
            "expected_completions": forecast.expected_completions,
            "completion_rate": forecast.completion_rate,
            "drop_rate": forecast.drop_rate,
            "confidence": forecast.confidence,
            "risk_weeks": risk_weeks(rows),
            "drop_pressure": drop_pressure(rows),
        }
    return matrix
