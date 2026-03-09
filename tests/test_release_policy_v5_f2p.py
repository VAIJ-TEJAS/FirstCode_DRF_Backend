from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_1001_high_risk_when_single_warning_and_large_change() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1400,
    )

    assert decision.risk_level == "high"
    assert decision.requires_rollback_plan is True


def test_f2p_1002_low_risk_when_warnings_absent_and_change_small() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.10",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is True
    assert decision.risk_level == "low"


def test_f2p_1003_release_rejected_when_reviewers_missing() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=False,
        change_size=300,
    )

    assert decision.approved is False
    assert any("Required reviewers" in blocker for blocker in decision.blockers)
