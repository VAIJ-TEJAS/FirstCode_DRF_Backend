from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, validate_rollout_plan


def test_f2p_1611_rollout_summary_tracks_internal_and_pilot() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r9",
        cohort_allocations={"internal": ["t1", "t2"], "pilot": ["t3"], "standard": []},
    )

    summary = rollout_summary(plan)

    assert summary["cohort_counts"]["internal"] == 2
    assert summary["traffic_total"] == 30


def test_f2p_1612_rollout_plan_has_no_validation_issues() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r10",
        cohort_allocations={"internal": ["t1"], "pilot": ["t2"], "standard": ["t3"], "long_tail": ["t4"]},
    )

    assert validate_rollout_plan(plan) == []
