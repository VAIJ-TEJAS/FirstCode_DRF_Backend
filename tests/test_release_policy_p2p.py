from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import build_release_context, evaluate_release_policy


def test_p2p_009_release_flow_compliant_case_is_approved() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.10",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=500,
    )

    assert decision.approved is True
    assert decision.risk_level in {"low", "medium"}


def test_p2p_010_release_flow_large_change_is_high_risk_even_if_approved() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1800,
    )

    assert decision.approved is True
    assert decision.risk_level == "high"
    assert decision.requires_rollback_plan is True


def test_p2p_011_release_flow_requires_reviewer_approval() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=False,
        change_size=200,
    )

    assert decision.approved is False
    assert any("reviewers" in blocker for blocker in decision.blockers)


def test_p2p_012_release_flow_runtime_errors_block_even_with_everything_else_green() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 1, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is False
    assert decision.risk_level == "critical"


def test_p2p_013_context_payload_tracks_operational_metadata() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=700,
    )

    assert context["branch"] == "main"
    assert context["ci_passed"] is True
    assert context["required_reviewers_approved"] is True
    assert "window_names" in context


def test_p2p_014_context_decision_mirrors_policy_engine_result() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=300,
    )

    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=300,
    )

    assert context["decision"]["approved"] == decision.approved


def test_p2p_015_hotfix_branch_is_allowed_path() -> None:
    decision = evaluate_release_policy(
        branch_name="hotfix",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=250,
    )

    assert decision.approved is True


def test_p2p_016_master_branch_is_still_treated_as_deployable() -> None:
    decision = evaluate_release_policy(
        branch_name="master",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=250,
    )

    assert decision.approved is True


def test_p2p_017_context_contains_rollback_plan_signal() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 4},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1650,
    )

    assert "requires_rollback_plan" in context["decision"]
    assert context["decision"]["requires_rollback_plan"] is True


def test_p2p_018_context_rollback_signal_false_for_small_low_risk_changes() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=250,
    )

    assert context["decision"]["requires_rollback_plan"] is False
