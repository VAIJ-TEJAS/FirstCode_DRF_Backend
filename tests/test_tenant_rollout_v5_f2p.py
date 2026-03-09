from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, tenants_for_cohort, validate_rollout_plan


def test_f2p_1011_rollout_plan_orders_cohorts_correctly() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r1",
        cohort_allocations={
            "internal": ["t1"],
            "pilot": ["t2"],
            "standard": ["t3", "t4"],
            "long_tail": ["t5"],
        },
    )

    assert [step.tenant_id for step in plan.steps] == ["t1", "t2", "t3", "t4", "t5"]


def test_f2p_1012_rollout_summary_counts_steps_and_traffic() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r2",
        cohort_allocations={"internal": ["t1", "t2"], "pilot": ["t3"]},
    )

    summary = rollout_summary(plan)

    assert summary["step_count"] == 3
    assert summary["cohort_counts"]["internal"] == 2
    assert summary["traffic_total"] == 30


def test_f2p_1013_validation_flags_invalid_percentages_and_duplicates() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r3",
        cohort_allocations={"internal": ["t1"], "pilot": ["t1"]},
        default_percentages={"pilot": 0},
    )

    issues = validate_rollout_plan(plan)

    assert any("Duplicate tenant" in issue for issue in issues)
    assert any("Traffic percent must be > 0" in issue for issue in issues)
    assert tenants_for_cohort(plan, "internal") == ["t1"]
