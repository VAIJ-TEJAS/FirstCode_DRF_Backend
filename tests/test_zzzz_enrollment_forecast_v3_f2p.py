from __future__ import annotations

from utils.enrollment_forecast import EnrollmentPoint, summarize_enrollment


def test_f2p_1499_medium_confidence_for_mid_volume_stable_conversions() -> None:
    summary = summarize_enrollment(
        program_id="prog-z",
        points=[
            EnrollmentPoint(week=1, leads=80, demos_completed=48, applications_started=30, applications_submitted=24, seats_confirmed=12),
            EnrollmentPoint(week=2, leads=80, demos_completed=48, applications_started=30, applications_submitted=24, seats_confirmed=12),
        ],
    )

    assert summary.confidence == "medium"
