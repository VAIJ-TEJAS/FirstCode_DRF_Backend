"""Placement projection and conversion utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class PlacementFunnel:
    month: str
    eligible_learners: int
    interview_scheduled: int
    interviews_cleared: int
    offers_received: int
    offers_accepted: int


@dataclass(frozen=True)
class PlacementProjection:
    quarter: str
    projected_accepts: int
    interview_clear_rate: float
    offer_rate: float
    accept_rate: float


def _rate(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def project_quarter(quarter: str, funnels: Iterable[PlacementFunnel]) -> PlacementProjection:
    rows = list(funnels)
    if not rows:
        return PlacementProjection(quarter=quarter, projected_accepts=0, interview_clear_rate=0.0, offer_rate=0.0, accept_rate=0.0)

    eligible = sum(max(0, item.eligible_learners) for item in rows)
    scheduled = sum(max(0, item.interview_scheduled) for item in rows)
    cleared = sum(max(0, item.interviews_cleared) for item in rows)
    offers = sum(max(0, item.offers_received) for item in rows)
    accepts = sum(max(0, item.offers_accepted) for item in rows)

    clear_rate = _rate(cleared, scheduled if scheduled > 0 else 1)
    offer_rate = _rate(offers, cleared if cleared > 0 else 1)
    accept_rate = _rate(accepts, offers if offers > 0 else 1)

    projected_accepts = int(round(eligible * (clear_rate / 100.0) * (offer_rate / 100.0) * (accept_rate / 100.0)))

    return PlacementProjection(
        quarter=quarter,
        projected_accepts=max(0, projected_accepts),
        interview_clear_rate=clear_rate,
        offer_rate=offer_rate,
        accept_rate=accept_rate,
    )


def monthly_accept_breakdown(funnels: Iterable[PlacementFunnel]) -> Dict[str, int]:
    return {item.month: max(0, item.offers_accepted) for item in funnels}
