from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, validate_rollout_plan


def test_f2p_1331_rollout_summary_matches_allocations() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r6",
        cohort_allocations={"internal": ["t1"], "pilot": ["t2", "t3"], "standard": ["t4"]},
    )

    summary = rollout_summary(plan)

    assert summary["step_count"] == 4
    assert summary["cohort_counts"]["pilot"] == 2


def test_f2p_1332_rollout_validation_passes_for_distinct_tenants() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r7",
        cohort_allocations={"internal": ["t1"], "pilot": ["t2"], "standard": ["t3"], "long_tail": ["t4"]},
    )

    assert validate_rollout_plan(plan) == []
