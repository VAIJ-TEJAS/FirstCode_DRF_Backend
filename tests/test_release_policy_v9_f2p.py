from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_1601_release_policy_allows_main_within_window() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=500,
    )

    assert decision.approved is True


def test_f2p_1602_release_policy_blocks_non_release_branch() -> None:
    decision = evaluate_release_policy(
        branch_name="feature/alpha",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=200,
    )

    assert decision.approved is False
    assert any("only allowed" in blocker.lower() for blocker in decision.blockers)
