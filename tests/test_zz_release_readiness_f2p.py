from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import decision_to_dict, evaluate_release_policy


def test_f2p_023_high_risk_decisions_require_explicit_rollback_plan() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 6},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1700,
    )

    payload = decision_to_dict(decision)

    assert payload["risk_level"] == "high"
    assert payload["requires_rollback_plan"] is True


def test_f2p_024_low_risk_release_does_not_require_rollback_plan() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    payload = decision_to_dict(decision)

    assert payload["risk_level"] in {"low", "medium"}
    assert payload["requires_rollback_plan"] is False


def test_f2p_025_critical_risk_keeps_rollback_plan_requirement_true() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 2, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=300,
    )

    payload = decision_to_dict(decision)

    assert payload["risk_level"] == "critical"
    assert payload["requires_rollback_plan"] is True
