from __future__ import annotations

from utils.tenant_rollout import (
    build_tenant_rollout_plan,
    rollout_summary,
    tenants_for_cohort,
    validate_rollout_plan,
)


def test_f2p_017_rollout_plan_respects_enterprise_cohort_order() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-100",
        cohort_allocations={
            "standard": ["tenant-3"],
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
        },
    )

    ordered = [step.tenant_id for step in plan.steps]
    assert ordered == ["tenant-1", "tenant-2", "tenant-3"]


def test_f2p_018_validation_reports_duplicate_tenants() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-101",
        cohort_allocations={"internal": ["tenant-1", "tenant-1"]},
    )

    issues = validate_rollout_plan(plan)

    assert any("Duplicate tenant" in issue for issue in issues)


def test_f2p_019_validation_flags_zero_traffic_steps() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-102",
        cohort_allocations={"internal": ["tenant-1"]},
        default_percentages={"internal": 0},
    )

    issues = validate_rollout_plan(plan)

    assert any("Traffic percent must be > 0" in issue for issue in issues)


def test_f2p_020_rollout_summary_includes_step_count_and_traffic_total() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-103",
        cohort_allocations={"internal": ["tenant-1"], "pilot": ["tenant-2"]},
        default_percentages={"internal": 10, "pilot": 20},
    )

    summary = rollout_summary(plan)

    assert summary["release_id"] == "rel-103"
    assert summary["step_count"] == 2
    assert summary["traffic_total"] == 30


def test_f2p_021_tenants_for_cohort_filters_exactly() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-104",
        cohort_allocations={
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
            "standard": ["tenant-3", "tenant-4"],
        },
    )

    assert tenants_for_cohort(plan, "standard") == ["tenant-3", "tenant-4"]


def test_f2p_022_unknown_cohort_entries_are_ignored_by_planner() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-105",
        cohort_allocations={
            "internal": ["tenant-1"],
            "experimental": ["tenant-x"],
        },
    )

    tenants = [step.tenant_id for step in plan.steps]
    assert "tenant-x" not in tenants
