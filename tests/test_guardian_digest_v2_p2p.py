from __future__ import annotations

from utils.guardian_communication import GuardianTouchpoint, build_digest, risk_learners


def test_p2p_1121_guardian_digest_and_risk_queue_are_consistent() -> None:
    rows = [
        GuardianTouchpoint("l1", "sms", "resolved", 20, False),
        GuardianTouchpoint("l2", "call", "delivered", 220, True),
        GuardianTouchpoint("l3", "email", "acknowledged", 150, False),
        GuardianTouchpoint("l2", "call", "resolved", 260, True),
    ]

    digest = build_digest(rows)
    risk = risk_learners(rows, response_threshold=180)

    assert digest.total_touchpoints == 4
    assert digest.success_rate == 100.0
    assert digest.escalation_rate == 50.0
    assert risk[0] == "l2"


def test_p2p_1122_guardian_digest_empty_rows_safe_defaults() -> None:
    digest = build_digest([])

    assert digest.total_touchpoints == 0
    assert digest.success_rate == 0.0
    assert digest.channel_mix == {}
