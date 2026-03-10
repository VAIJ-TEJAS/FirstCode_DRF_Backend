from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EntitlementPlan:
    seats: int
    support_tier: str
    analytics_access: bool


def build_entitlement_plan(seats: int, support_tier: str) -> EntitlementPlan:
    analytics_access = support_tier in {"enterprise", "premium"} and seats >= 50
    return EntitlementPlan(seats=seats, support_tier=support_tier, analytics_access=analytics_access)


def entitlement_snapshot(plans: Dict[str, EntitlementPlan]) -> dict:
    return {
        "total_accounts": len(plans),
        "enterprise_accounts": sum(1 for plan in plans.values() if plan.support_tier == "enterprise"),
        "analytics_enabled": sum(1 for plan in plans.values() if plan.analytics_access),
    }
