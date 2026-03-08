"""Tenant rollout utilities used by backend release orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class TenantRolloutStep:
    tenant_id: str
    order: int
    cohort: str
    traffic_percent: int


@dataclass(frozen=True)
class TenantRolloutPlan:
    release_id: str
    steps: List[TenantRolloutStep]


COHORT_ORDER = ["internal", "pilot", "standard", "long_tail"]


def _normalize_percent(value: int) -> int:
    if value < 0:
        return 0
    if value > 100:
        return 100
    return int(value)


def build_tenant_rollout_plan(
    release_id: str,
    cohort_allocations: Dict[str, List[str]],
    default_percentages: Dict[str, int] | None = None,
) -> TenantRolloutPlan:
    percentages = {
        "internal": 5,
        "pilot": 20,
        "standard": 50,
        "long_tail": 25,
    }

    if default_percentages:
        percentages.update(default_percentages)

    steps: List[TenantRolloutStep] = []
    order = 1

    for cohort in COHORT_ORDER:
        tenant_ids = list(cohort_allocations.get(cohort, []))
        share = _normalize_percent(percentages.get(cohort, 0))

        for tenant_id in tenant_ids:
            steps.append(
                TenantRolloutStep(
                    tenant_id=tenant_id,
                    order=order,
                    cohort=cohort,
                    traffic_percent=share,
                )
            )
            order += 1

    return TenantRolloutPlan(release_id=release_id, steps=steps)


def validate_rollout_plan(plan: TenantRolloutPlan) -> List[str]:
    issues: List[str] = []

    seen_tenants = set()

    for step in plan.steps:
        if not step.tenant_id:
            issues.append("Tenant rollout step has empty tenant id.")

        if step.tenant_id in seen_tenants:
            issues.append(f"Duplicate tenant found in rollout plan: {step.tenant_id}")
        seen_tenants.add(step.tenant_id)

        if step.cohort not in COHORT_ORDER:
            issues.append(f"Unknown cohort in rollout plan: {step.cohort}")

        if step.traffic_percent <= 0:
            issues.append(f"Traffic percent must be > 0 for tenant: {step.tenant_id}")

    return issues


def rollout_summary(plan: TenantRolloutPlan) -> Dict[str, object]:
    cohort_counts: Dict[str, int] = {cohort: 0 for cohort in COHORT_ORDER}
    traffic_total = 0

    for step in plan.steps:
        cohort_counts[step.cohort] = cohort_counts.get(step.cohort, 0) + 1
        traffic_total += step.traffic_percent

    return {
        "release_id": plan.release_id,
        "step_count": len(plan.steps),
        "cohort_counts": cohort_counts,
        "traffic_total": traffic_total,
    }


def tenants_for_cohort(plan: TenantRolloutPlan, cohort: str) -> List[str]:
    return [step.tenant_id for step in plan.steps if step.cohort == cohort]
