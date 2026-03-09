from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_201_warning_heavy_1001_line_release_is_high_risk() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 3},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1001,
    )

    assert decision.risk_level == "high"


def test_f2p_202_warning_heavy_1000_line_release_remains_medium_risk() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 3},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1000,
    )

    assert decision.risk_level == "medium"


def test_f2p_203_new_high_risk_rule_still_requires_rollback_plan() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 12, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 3},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1100,
    )

    assert decision.requires_rollback_plan is True
