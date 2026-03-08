from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import decision_to_dict, evaluate_release_policy


def test_p2p_101_release_policy_matrix_low_risk_case_stays_low() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=180,
    )

    assert decision.approved is True
    assert decision.risk_level == "low"


def test_p2p_102_release_policy_matrix_medium_risk_from_warning_count() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=400,
    )

    assert decision.approved is True
    assert decision.risk_level == "medium"


def test_p2p_103_release_policy_matrix_high_risk_from_very_large_change() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1700,
    )

    assert decision.approved is True
    assert decision.risk_level == "high"


def test_p2p_104_release_policy_matrix_critical_when_runtime_has_errors() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 1, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is False
    assert decision.risk_level == "critical"


def test_p2p_105_release_policy_matrix_dict_payload_contains_rollback_flag() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    payload = decision_to_dict(decision)

    assert "requires_rollback_plan" in payload
