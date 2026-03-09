from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, validate_rollout_plan


def test_p2p_1421_rollout_plan_traffic_total_matches_cohort_defaults() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r7",
        cohort_allocations={"internal": ["t1"], "pilot": ["t2"], "standard": ["t3"], "long_tail": ["t4"]},
    )

    summary = rollout_summary(plan)

    assert summary["traffic_total"] == 100
    assert summary["step_count"] == 4


def test_p2p_1422_rollout_plan_validates_clean_input() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r8",
        cohort_allocations={"internal": ["x1"], "pilot": ["x2"]},
    )

    assert validate_rollout_plan(plan) == []
