"""Marketplace risk and partner quality scoring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class MarketplacePartner:
    partner_id: str
    satisfaction_percent: float
    fulfillment_percent: float
    escalation_count: int
    region: str


@dataclass(frozen=True)
class MarketplaceRisk:
    partner_id: str
    risk_score: float
    tier: str
    actions: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_partner(row: MarketplacePartner) -> MarketplaceRisk:
    score = _clamp(row.satisfaction_percent * 0.45 + row.fulfillment_percent * 0.45 - row.escalation_count * 5)
    tier = "low"
    actions: List[str] = []

    if score < 70:
        tier = "medium"
        actions.append("partner-coaching")
    if score < 50:
        tier = "high"
        actions.append("pause-leads")

    return MarketplaceRisk(row.partner_id, round(score, 2), tier, actions)


def region_mix(rows: Iterable[MarketplacePartner]) -> Dict[str, int]:
    mix: Dict[str, int] = {}
    for row in rows:
        mix[row.region] = mix.get(row.region, 0) + 1
    return mix


def risk_ranking(rows: Iterable[MarketplacePartner]) -> List[MarketplaceRisk]:
    return sorted([evaluate_partner(row) for row in rows], key=lambda item: item.risk_score)


def high_risk_partners(rows: Iterable[MarketplacePartner]) -> List[str]:
    return [item.partner_id for item in risk_ranking(rows) if item.tier == "high"]


def marketplace_digest(rows: Iterable[MarketplacePartner]) -> Dict[str, object]:
    risks = risk_ranking(rows)
    return {
        "total_partners": len(risks),
        "high_risk": len([item for item in risks if item.tier == "high"]),
        "region_mix": region_mix(rows),
        "top_partner": risks[0].partner_id if risks else None,
    }


def risk_actions(rows: Iterable[MarketplacePartner]) -> Dict[str, List[str]]:
    return {item.partner_id: item.actions for item in risk_ranking(rows)}


def stability_index(rows: Iterable[MarketplacePartner]) -> float:
    risks = risk_ranking(rows)
    if not risks:
        return 100.0
    return round(sum(item.risk_score for item in risks) / len(risks), 2)


def tier_summary(rows: Iterable[MarketplacePartner]) -> Dict[str, int]:
    summary = {"low": 0, "medium": 0, "high": 0}
    for item in risk_ranking(rows):
        summary[item.tier] += 1
    return summary


def average_actions(rows: Iterable[MarketplacePartner]) -> float:
    risks = risk_ranking(rows)
    if not risks:
        return 0.0
    return round(sum(len(item.actions) for item in risks) / len(risks), 2)
