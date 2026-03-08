from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_101_warning_heavy_large_rollouts_are_marked_high_risk() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 4},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=950,
    )

    assert decision.risk_level == "high"


def test_f2p_102_warning_heavy_small_rollouts_remain_medium_risk() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 4},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=350,
    )

    assert decision.risk_level == "medium"


def test_f2p_103_zero_warning_large_rollout_uses_existing_large_change_risk_path() -> None:
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 10, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 0},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1700,
    )

    assert decision.risk_level == "high"
