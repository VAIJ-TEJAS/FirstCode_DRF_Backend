"""Exam supply chain tracking for enterprise testing operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SupplyBatch:
    batch_id: str
    region: str
    devices_ready: int
    devices_in_use: int
    devices_blocked: int


@dataclass(frozen=True)
class SupplySignal:
    region: str
    utilization_percent: float
    blocked_percent: float
    status: str


def _percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def evaluate_supply(batches: Iterable[SupplyBatch], region: str) -> SupplySignal:
    rows = [item for item in batches if item.region == region]
    if not rows:
        return SupplySignal(region, 0.0, 0.0, "stable")

    ready = sum(max(0, item.devices_ready) for item in rows)
    in_use = sum(max(0, item.devices_in_use) for item in rows)
    blocked = sum(max(0, item.devices_blocked) for item in rows)

    utilization = _percent(in_use, max(1, ready + in_use))
    blocked_percent = _percent(blocked, max(1, ready + in_use))

    status = "stable"
    if utilization >= 80 or blocked_percent >= 10:
        status = "watch"
    if utilization >= 95 or blocked_percent >= 20:
        status = "critical"

    return SupplySignal(region, utilization, blocked_percent, status)


def region_supply_map(batches: Iterable[SupplyBatch]) -> Dict[str, SupplySignal]:
    regions = sorted({item.region for item in batches})
    return {region: evaluate_supply(batches, region) for region in regions}


def critical_regions(batches: Iterable[SupplyBatch]) -> List[str]:
    return [region for region, signal in region_supply_map(batches).items() if signal.status == "critical"]


def supply_digest(batches: Iterable[SupplyBatch]) -> Dict[str, object]:
    map_data = region_supply_map(batches)
    return {
        "regions": list(map_data.keys()),
        "critical_regions": critical_regions(batches),
        "utilization": {region: signal.utilization_percent for region, signal in map_data.items()},
        "blocked": {region: signal.blocked_percent for region, signal in map_data.items()},
    }


def capacity_by_region(batches: Iterable[SupplyBatch]) -> Dict[str, int]:
    totals: Dict[str, int] = {}
    for batch in batches:
        totals[batch.region] = totals.get(batch.region, 0) + max(0, batch.devices_ready + batch.devices_in_use)
    return totals


def supply_pressure(batches: Iterable[SupplyBatch]) -> Dict[str, float]:
    pressures: Dict[str, float] = {}
    for region, signal in region_supply_map(batches).items():
        pressures[region] = round(signal.utilization_percent + signal.blocked_percent, 2)
    return pressures


def batch_utilization(batches: Iterable[SupplyBatch]) -> Dict[str, float]:
    utilization: Dict[str, float] = {}
    for batch in batches:
        total = max(1, batch.devices_ready + batch.devices_in_use)
        utilization[batch.batch_id] = round((max(0, batch.devices_in_use) / total) * 100.0, 2)
    return utilization


def supply_score(batches: Iterable[SupplyBatch], region: str) -> float:
    signal = evaluate_supply(batches, region)
    return round(100.0 - signal.blocked_percent - (signal.utilization_percent / 2.0), 2)
