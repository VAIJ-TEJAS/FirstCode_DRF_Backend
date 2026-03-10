from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class EscalationTier:
    tier: str
    threshold_hours: int
    owner: str


@dataclass(frozen=True)
class EscalationPolicy:
    policy_id: str
    tiers: List[EscalationTier]


def resolve_escalation(policy: EscalationPolicy, age_hours: int) -> dict:
    tiers = sorted(policy.tiers, key=lambda item: item.threshold_hours)
    selected = tiers[0]
    for tier in tiers:
        if age_hours >= tier.threshold_hours:
            selected = tier
    return {"policy_id": policy.policy_id, "tier": selected.tier, "owner": selected.owner}


def escalation_summary(policy: EscalationPolicy) -> dict:
    max_tier = max(policy.tiers, key=lambda item: item.threshold_hours)
    return {"policy_id": policy.policy_id, "max_tier": max_tier}
