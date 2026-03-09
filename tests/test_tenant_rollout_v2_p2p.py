from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, tenants_for_cohort, validate_rollout_plan


def test_p2p_210_rollout_plan_maintains_defined_cohort_order() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-900",
        cohort_allocations={
            "standard": ["tenant-3"],
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
        },
    )

    tenant_order = [step.tenant_id for step in plan.steps]
    assert tenant_order == ["tenant-1", "tenant-2", "tenant-3"]


def test_p2p_211_rollout_summary_reports_step_count_and_traffic_total() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-901",
        cohort_allocations={"internal": ["tenant-1"], "pilot": ["tenant-2"]},
        default_percentages={"internal": 10, "pilot": 20},
    )

    summary = rollout_summary(plan)

    assert summary["step_count"] == 2
    assert summary["traffic_total"] == 30


def test_p2p_212_validate_rollout_plan_catches_duplicate_tenants() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-902",
        cohort_allocations={"internal": ["tenant-1", "tenant-1"]},
    )

    issues = validate_rollout_plan(plan)

    assert any("Duplicate tenant" in issue for issue in issues)


def test_p2p_213_tenants_for_cohort_filters_without_cross_contamination() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-903",
        cohort_allocations={
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
            "standard": ["tenant-3", "tenant-4"],
        },
    )

    assert tenants_for_cohort(plan, "standard") == ["tenant-3", "tenant-4"]
    assert tenants_for_cohort(plan, "internal") == ["tenant-1"]
