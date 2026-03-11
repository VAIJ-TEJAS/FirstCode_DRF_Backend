from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_1603_warning_1400_is_high() -> None:
    # F2P-1603
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1400,
    )

    assert decision.risk_level == "high"
