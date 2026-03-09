from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import build_release_context, decision_to_dict, evaluate_release_policy


def test_p2p_401_release_policy_green_path_remains_approved() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=300,
    )

    assert decision.approved is True


def test_p2p_402_release_policy_reviewer_gate_still_blocks_without_approval() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=False,
        change_size=300,
    )

    assert decision.approved is False
    assert any("reviewers" in blocker for blocker in decision.blockers)


def test_p2p_403_release_context_decision_includes_rollback_flag() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1400,
    )

    assert "requires_rollback_plan" in context["decision"]


def test_p2p_404_decision_to_dict_shape_remains_stable() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.20",
        now_utc=datetime(2026, 3, 20, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=500,
    )

    payload = decision_to_dict(decision)

    assert "approved" in payload
    assert "risk_level" in payload
    assert "blockers" in payload
    assert "requires_rollback_plan" in payload
