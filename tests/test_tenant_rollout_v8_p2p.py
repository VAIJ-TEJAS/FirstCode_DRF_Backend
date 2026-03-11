from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary


def test_p2p_1521_rollout_summary_counts_all_cohorts() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r8",
        cohort_allocations={
            "internal": ["t1"],
            "pilot": ["t2"],
            "standard": ["t3"],
            "long_tail": ["t4"],
        },
    )

    summary = rollout_summary(plan)

    assert summary["step_count"] == 4
    assert summary["cohort_counts"]["long_tail"] == 1
