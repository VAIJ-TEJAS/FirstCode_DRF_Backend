from __future__ import annotations

from datetime import datetime, timezone

from utils.release_policy import evaluate_release_policy


def test_f2p_1601_single_warning_1300_is_not_high() -> None:
    # F2P-1601
    decision = evaluate_release_policy(
        branch_name="main",
        now_utc=datetime(2026, 3, 11, 8, 0, tzinfo=timezone.utc),
        runtime_summary={"error": 0, "warning": 1},
        ci_passed=True,
        required_reviewers_approved=True,
        change_size=1300,
    )

    assert decision.risk_level in {"low", "medium"}
