from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_1801_release_policy_allows_release_branch() -> None:
    decision = evaluate_release_policy(
        branch_name="release/2026.03.10",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=450,
    )

    assert decision.approved is True
