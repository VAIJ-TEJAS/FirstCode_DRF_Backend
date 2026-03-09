from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, tenants_for_cohort, validate_rollout_plan


def test_p2p_408_tenant_rollout_ordering_stays_internal_to_long_tail() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-2001",
        cohort_allocations={
            "standard": ["tenant-3"],
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
            "long_tail": ["tenant-4"],
        },
    )

    assert [step.tenant_id for step in plan.steps] == ["tenant-1", "tenant-2", "tenant-3", "tenant-4"]


def test_p2p_409_rollout_summary_retains_step_and_traffic_contract() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-2002",
        cohort_allocations={"internal": ["tenant-1"], "pilot": ["tenant-2"]},
        default_percentages={"internal": 12, "pilot": 24},
    )

    summary = rollout_summary(plan)

    assert summary["step_count"] == 2
    assert summary["traffic_total"] == 36


def test_p2p_410_validate_rollout_detects_duplicates_and_zero_percent() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-2003",
        cohort_allocations={"internal": ["tenant-1", "tenant-1"]},
        default_percentages={"internal": 0},
    )

    issues = validate_rollout_plan(plan)

    assert any("Duplicate tenant" in issue for issue in issues)
    assert any("Traffic percent" in issue for issue in issues)


def test_p2p_411_tenants_for_cohort_selects_requested_bucket() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-2004",
        cohort_allocations={
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
            "standard": ["tenant-3", "tenant-4"],
        },
    )

    assert tenants_for_cohort(plan, "standard") == ["tenant-3", "tenant-4"]
