from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, tenants_for_cohort, validate_rollout_plan


def test_p2p_308_tenant_rollout_plan_keeps_priority_order() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-1001",
        cohort_allocations={
            "standard": ["tenant-3"],
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
        },
    )

    assert [step.tenant_id for step in plan.steps] == ["tenant-1", "tenant-2", "tenant-3"]


def test_p2p_309_rollout_summary_reports_expected_contract() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-1002",
        cohort_allocations={"internal": ["tenant-1"], "pilot": ["tenant-2"]},
        default_percentages={"internal": 10, "pilot": 20},
    )

    summary = rollout_summary(plan)

    assert summary["release_id"] == "rel-1002"
    assert summary["step_count"] == 2
    assert summary["traffic_total"] == 30


def test_p2p_310_validate_rollout_plan_detects_duplicates() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-1003",
        cohort_allocations={"internal": ["tenant-1", "tenant-1"]},
    )

    issues = validate_rollout_plan(plan)

    assert any("Duplicate tenant" in issue for issue in issues)


def test_p2p_311_tenants_for_cohort_filters_precisely() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-1004",
        cohort_allocations={
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
            "standard": ["tenant-3", "tenant-4"],
        },
    )

    assert tenants_for_cohort(plan, "standard") == ["tenant-3", "tenant-4"]
