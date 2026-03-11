"""Placement radar analytics helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class PlacementSignal:
    learner_id: str
    interviews_scheduled: int
    interviews_cleared: int
    offers_received: int
    offers_accepted: int


@dataclass(frozen=True)
class PlacementRadar:
    total_learners: int
    clear_rate: float
    offer_rate: float
    accept_rate: float
    projected_accepts: int


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def summarize_radar(signals: Iterable[PlacementSignal]) -> PlacementRadar:
    rows = list(signals)
    scheduled = sum(max(0, row.interviews_scheduled) for row in rows)
    cleared = sum(max(0, row.interviews_cleared) for row in rows)
    offers = sum(max(0, row.offers_received) for row in rows)
    accepts = sum(max(0, row.offers_accepted) for row in rows)

    clear_rate = _rate(cleared, scheduled if scheduled > 0 else 1)
    offer_rate = _rate(offers, cleared if cleared > 0 else 1)
    accept_rate = _rate(accepts, offers if offers > 0 else 1)

    projected_accepts = int(round((len(rows) * clear_rate * offer_rate * accept_rate) / 1000000))

    return PlacementRadar(
        total_learners=len(rows),
        clear_rate=clear_rate,
        offer_rate=offer_rate,
        accept_rate=accept_rate,
        projected_accepts=projected_accepts,
    )


def radar_heatmap(signals: Iterable[PlacementSignal]) -> Dict[str, int]:
    return {row.learner_id: max(0, row.offers_accepted) for row in signals}


def success_candidates(signals: Iterable[PlacementSignal], min_offers: int = 1) -> List[str]:
    return [row.learner_id for row in signals if row.offers_received >= min_offers and row.offers_accepted > 0]


def radar_digest(signals: Iterable[PlacementSignal]) -> Dict[str, object]:
    radar = summarize_radar(signals)
    return {
        "total_learners": radar.total_learners,
        "clear_rate": radar.clear_rate,
        "offer_rate": radar.offer_rate,
        "accept_rate": radar.accept_rate,
        "projected_accepts": radar.projected_accepts,
        "success_candidates": success_candidates(signals),
    }


def placement_risk(signals: Iterable[PlacementSignal], min_clear_rate: float = 50.0) -> List[str]:
    radar = summarize_radar(signals)
    if radar.clear_rate >= min_clear_rate:
        return []
    return [row.learner_id for row in signals if row.interviews_cleared == 0]


def acceptance_distribution(signals: Iterable[PlacementSignal]) -> Dict[str, int]:
    distribution = {"none": 0, "one": 0, "multiple": 0}
    for row in signals:
        if row.offers_accepted == 0:
            distribution["none"] += 1
        elif row.offers_accepted == 1:
            distribution["one"] += 1
        else:
            distribution["multiple"] += 1
    return distribution


def pipeline_pressure(signals: Iterable[PlacementSignal]) -> float:
    radar = summarize_radar(signals)
    if radar.total_learners == 0:
        return 0.0
    return round((radar.offer_rate + radar.accept_rate) / 2.0, 2)


def projected_accepts_matrix(signals: Iterable[PlacementSignal], cohorts: Dict[str, List[PlacementSignal]]) -> Dict[str, int]:
    matrix: Dict[str, int] = {}
    matrix["overall"] = summarize_radar(signals).projected_accepts
    for cohort_id, rows in cohorts.items():
        matrix[cohort_id] = summarize_radar(rows).projected_accepts
    return matrix


def placement_digest(signals: Iterable[PlacementSignal]) -> Dict[str, object]:
    radar = summarize_radar(signals)
    return {
        "total_learners": radar.total_learners,
        "clear_rate": radar.clear_rate,
        "offer_rate": radar.offer_rate,
        "accept_rate": radar.accept_rate,
        "projected_accepts": radar.projected_accepts,
        "pipeline_pressure": pipeline_pressure(signals),
    }
