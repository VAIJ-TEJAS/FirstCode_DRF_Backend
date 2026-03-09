from __future__ import annotations

from utils.enrollment_forecast import EnrollmentPoint, cohort_pressure, summarize_enrollment


def test_f2p_1101_enrollment_forecast_builds_conversion_rates() -> None:
    summary = summarize_enrollment(
        program_id="prog-a",
        points=[
            EnrollmentPoint(week=1, leads=220, demos_completed=132, applications_started=88, applications_submitted=66, seats_confirmed=44),
            EnrollmentPoint(week=2, leads=240, demos_completed=144, applications_started=96, applications_submitted=72, seats_confirmed=48),
        ],
    )

    assert summary.expected_seats_next_cycle > 0
    assert summary.lead_to_demo_rate == 60.0
    assert summary.confidence in {"medium", "high"}


def test_f2p_1102_cohort_pressure_uses_confirmed_vs_target() -> None:
    pressure = cohort_pressure(
        points=[
            EnrollmentPoint(week=1, leads=200, demos_completed=120, applications_started=80, applications_submitted=60, seats_confirmed=40),
            EnrollmentPoint(week=2, leads=210, demos_completed=126, applications_started=84, applications_submitted=63, seats_confirmed=42),
        ],
        seat_target=100,
    )

    assert pressure == 82.0
