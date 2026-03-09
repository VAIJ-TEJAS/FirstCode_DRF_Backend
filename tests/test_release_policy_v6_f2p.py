from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import build_release_context, decision_to_dict, evaluate_release_policy, release_window_names


def test_f2p_1201_release_context_contains_stable_policy_fields() -> None:
    context = build_release_context(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=600,
    )

    assert context["branch"] == "main"
    assert "decision" in context
    assert "window_names" in context


def test_f2p_1202_release_window_names_expose_defaults() -> None:
    names = release_window_names()
    assert "weekday-morning" in names
    assert "weekday-evening" in names


def test_f2p_1203_decision_payload_has_expected_schema() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=500,
    )

    payload = decision_to_dict(decision)

    assert set(payload.keys()) == {
        "approved",
        "reason",
        "blockers",
        "risk_level",
        "requires_rollback_plan",
    }


def test_f2p_1204_release_policy_escalates_critical_on_runtime_errors() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.10",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 2, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=120,
    )

    assert decision.risk_level == "critical"
    assert decision.approved is False


def test_f2p_1205_release_policy_requires_rollback_for_extreme_change() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1700,
    )

    assert decision.requires_rollback_plan is True
    assert decision.risk_level == "high"
