"""Learning operations dashboard signals for enterprise oversight."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class OpsSignal:
    signal_id: str
    category: str
    severity: str
    impacted_learners: int
    owner_team: str


@dataclass(frozen=True)
class OpsRollup:
    total_signals: int
    critical_count: int
    impacted_learners: int
    owner_load: Dict[str, int]


def summarize_ops(signals: Iterable[OpsSignal]) -> OpsRollup:
    rows = list(signals)
    total = len(rows)
    critical = len([row for row in rows if row.severity == "critical"])
    impacted = sum(max(0, row.impacted_learners) for row in rows)
    owner_load: Dict[str, int] = {}

    for row in rows:
        owner_load[row.owner_team] = owner_load.get(row.owner_team, 0) + 1

    return OpsRollup(total, critical, impacted, owner_load)


def severity_mix(signals: Iterable[OpsSignal]) -> Dict[str, int]:
    mix: Dict[str, int] = {}
    for row in signals:
        mix[row.severity] = mix.get(row.severity, 0) + 1
    return mix


def top_categories(signals: Iterable[OpsSignal], limit: int = 3) -> List[str]:
    counts: Dict[str, int] = {}
    for row in signals:
        counts[row.category] = counts.get(row.category, 0) + 1
    return [item[0] for item in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[: max(1, limit)]]


def owner_workload(signals: Iterable[OpsSignal]) -> Dict[str, int]:
    workload: Dict[str, int] = {}
    for row in signals:
        workload[row.owner_team] = workload.get(row.owner_team, 0) + row.impacted_learners
    return workload


def ops_digest(signals: Iterable[OpsSignal]) -> Dict[str, object]:
    rollup = summarize_ops(signals)
    return {
        "total_signals": rollup.total_signals,
        "critical_count": rollup.critical_count,
        "impacted_learners": rollup.impacted_learners,
        "severity_mix": severity_mix(signals),
        "top_categories": top_categories(signals),
        "owner_workload": owner_workload(signals),
    }


def category_pressure(signals: Iterable[OpsSignal]) -> Dict[str, float]:
    counts: Dict[str, int] = {}
    impacted: Dict[str, int] = {}
    for row in signals:
        counts[row.category] = counts.get(row.category, 0) + 1
        impacted[row.category] = impacted.get(row.category, 0) + max(0, row.impacted_learners)
    return {key: round(impacted[key] / max(1, counts[key]), 2) for key in counts}


def workload_bands(signals: Iterable[OpsSignal]) -> Dict[str, str]:
    workload = owner_workload(signals)
    bands: Dict[str, str] = {}
    for owner, value in workload.items():
        bands[owner] = "high" if value > 500 else "medium" if value > 200 else "low"
    return bands


def signals_by_owner(signals: Iterable[OpsSignal]) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    for row in signals:
        result.setdefault(row.owner_team, []).append(row.signal_id)
    return result


def signal_count(signals: Iterable[OpsSignal]) -> int:
    return len(list(signals))
