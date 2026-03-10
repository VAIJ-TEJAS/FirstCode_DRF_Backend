"""Vendor risk evaluation helpers for enterprise procurement."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class VendorProfile:
    vendor_id: str
    compliance_score: float
    uptime_percent: float
    breach_count: int
    region: str


@dataclass(frozen=True)
class VendorRisk:
    vendor_id: str
    risk_score: float
    tier: str
    actions: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_vendor(profile: VendorProfile) -> VendorRisk:
    score = _clamp(profile.compliance_score * 0.4 + profile.uptime_percent * 0.4 - profile.breach_count * 8)
    tier = "low"
    actions: List[str] = []

    if score < 70:
        tier = "medium"
        actions.append("schedule-audit")
    if score < 50:
        tier = "high"
        actions.append("freeze-procurement")

    return VendorRisk(profile.vendor_id, round(score, 2), tier, actions)


def region_risk_mix(profiles: Iterable[VendorProfile]) -> Dict[str, int]:
    mix: Dict[str, int] = {}
    for profile in profiles:
        mix[profile.region] = mix.get(profile.region, 0) + 1
    return mix


def risk_digest(profiles: Iterable[VendorProfile]) -> Dict[str, object]:
    rows = list(profiles)
    risks = [evaluate_vendor(row) for row in rows]
    high = len([item for item in risks if item.tier == "high"])
    return {
        "total_vendors": len(rows),
        "high_risk": high,
        "region_mix": region_risk_mix(rows),
    }


def risk_ranking(profiles: Iterable[VendorProfile]) -> List[VendorRisk]:
    return sorted([evaluate_vendor(row) for row in profiles], key=lambda item: item.risk_score)


def high_risk_vendors(profiles: Iterable[VendorProfile]) -> List[str]:
    return [item.vendor_id for item in risk_ranking(profiles) if item.tier == "high"]
