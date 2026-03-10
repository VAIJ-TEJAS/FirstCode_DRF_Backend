from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary


def test_f2p_1811_rollout_summary_respects_default_percentages() -> None:
    plan = build_tenant_rollout_plan(
        release_id="r12",
        cohort_allocations={"internal": ["t1"], "pilot": ["t2"], "standard": ["t3"], "long_tail": ["t4"]},
    )

    summary = rollout_summary(plan)

    assert summary["traffic_total"] == 100
