from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import build_release_context, decision_to_dict, evaluate_release_policy


def test_p2p_301_release_policy_all_green_stays_approved() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=400,
    )

    assert decision.approved is True
    assert decision.risk_level == "low"


def test_p2p_302_release_policy_runtime_errors_remain_critical_and_blocking() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 2, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=300,
    )

    assert decision.approved is False
    assert decision.risk_level == "critical"


def test_p2p_303_release_context_contains_full_decision_contract() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=900,
    )

    decision = context["decision"]

    assert "approved" in decision
    assert "risk_level" in decision
    assert "requires_rollback_plan" in decision


def test_p2p_304_decision_to_dict_structure_is_stable() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.15",
        now_utc=datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=600,
    )

    payload = decision_to_dict(decision)

    assert isinstance(payload["approved"], bool)
    assert isinstance(payload["blockers"], list)
    assert isinstance(payload["reason"], str)
