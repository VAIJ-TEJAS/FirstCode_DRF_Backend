from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import build_release_context, decision_to_dict, evaluate_release_policy


def test_p2p_201_main_branch_green_pipeline_remains_approved() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=500,
    )

    assert decision.approved is True


def test_p2p_202_blocker_appears_when_reviewer_approval_missing() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=False,
        change_size=200,
    )

    assert decision.approved is False
    assert any("reviewers" in blocker for blocker in decision.blockers)


def test_p2p_203_release_context_contains_decision_payload_with_rollback() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1200,
    )

    assert "decision" in context
    assert "requires_rollback_plan" in context["decision"]


def test_p2p_204_decision_payload_remains_serializable_contract() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.12",
        now_utc=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=150,
    )

    payload = decision_to_dict(decision)

    assert isinstance(payload["approved"], bool)
    assert isinstance(payload["blockers"], list)
    assert "risk_level" in payload
    assert "requires_rollback_plan" in payload


def test_p2p_205_outside_window_still_blocks_even_with_low_risk() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 12, 2, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=120,
    )

    assert decision.approved is False
    assert any("outside approved release windows" in blocker for blocker in decision.blockers)
