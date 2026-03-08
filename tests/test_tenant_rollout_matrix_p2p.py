from __future__ import annotations

from utils.tenant_rollout import build_tenant_rollout_plan, rollout_summary, validate_rollout_plan


def test_p2p_111_tenant_rollout_matrix_plans_internal_then_pilot_then_standard() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-300",
        cohort_allocations={
            "standard": ["tenant-3"],
            "internal": ["tenant-1"],
            "pilot": ["tenant-2"],
        },
    )

    order = [step.tenant_id for step in plan.steps]
    assert order == ["tenant-1", "tenant-2", "tenant-3"]


def test_p2p_112_tenant_rollout_matrix_summary_counts_steps() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-301",
        cohort_allocations={"internal": ["tenant-1"], "pilot": ["tenant-2"]},
    )

    summary = rollout_summary(plan)

    assert summary["step_count"] == 2


def test_p2p_113_tenant_rollout_matrix_detects_zero_percent_invalid_step() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-302",
        cohort_allocations={"internal": ["tenant-1"]},
        default_percentages={"internal": 0},
    )

    issues = validate_rollout_plan(plan)

    assert any("Traffic percent" in issue for issue in issues)


def test_p2p_114_tenant_rollout_matrix_detects_duplicate_tenants() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-303",
        cohort_allocations={"internal": ["tenant-1", "tenant-1"]},
    )

    issues = validate_rollout_plan(plan)

    assert any("Duplicate tenant" in issue for issue in issues)


def test_p2p_115_tenant_rollout_matrix_ignores_unknown_cohorts() -> None:
    plan = build_tenant_rollout_plan(
        release_id="rel-304",
        cohort_allocations={"internal": ["tenant-1"], "sandbox": ["tenant-x"]},
    )

    tenant_ids = [step.tenant_id for step in plan.steps]
    assert "tenant-x" not in tenant_ids
