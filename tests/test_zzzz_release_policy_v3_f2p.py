from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_301_two_warnings_with_851_change_size_is_now_high_risk() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=851,
    )

    assert decision.risk_level == "high"


def test_f2p_302_two_warnings_with_850_change_size_remains_medium() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=850,
    )

    assert decision.risk_level == "medium"


def test_f2p_303_new_high_risk_path_requires_rollback_plan() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 15, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 2},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=900,
    )

    assert decision.requires_rollback_plan is True
