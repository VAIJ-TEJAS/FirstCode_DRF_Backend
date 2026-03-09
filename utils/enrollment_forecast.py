"""Enrollment forecast primitives for enterprise growth planning."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class EnrollmentPoint:
    week: int
    leads: int
    demos_completed: int
    applications_started: int
    applications_submitted: int
    seats_confirmed: int


@dataclass(frozen=True)
class ForecastSummary:
    program_id: str
    expected_seats_next_cycle: int
    lead_to_demo_rate: float
    demo_to_application_rate: float
    application_to_seat_rate: float
    confidence: str


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round((numerator / denominator) * 100.0, 2)


def _confidence(variation: float, volume: int) -> str:
    if volume < 150:
        return "low"
    if variation > 18:
        return "medium"
    return "high"


def summarize_enrollment(program_id: str, points: Iterable[EnrollmentPoint]) -> ForecastSummary:
    rows = list(points)
    if not rows:
        return ForecastSummary(program_id, 0, 0.0, 0.0, 0.0, "low")

    lead_to_demo = [_safe_rate(item.demos_completed, item.leads) for item in rows if item.leads > 0]
    demo_to_app = [_safe_rate(item.applications_started, item.demos_completed) for item in rows if item.demos_completed > 0]
    app_to_seat = [_safe_rate(item.seats_confirmed, item.applications_submitted) for item in rows if item.applications_submitted > 0]

    avg_lead_to_demo = round(mean(lead_to_demo), 2) if lead_to_demo else 0.0
    avg_demo_to_app = round(mean(demo_to_app), 2) if demo_to_app else 0.0
    avg_app_to_seat = round(mean(app_to_seat), 2) if app_to_seat else 0.0

    total_leads = sum(max(0, item.leads) for item in rows)
    expected = int(round(total_leads * (avg_lead_to_demo / 100.0) * (avg_demo_to_app / 100.0) * (avg_app_to_seat / 100.0)))

    variation = 0.0
    if len(app_to_seat) >= 2:
        variation = max(app_to_seat) - min(app_to_seat)

    confidence = _confidence(variation=variation, volume=total_leads)

    return ForecastSummary(
        program_id=program_id,
        expected_seats_next_cycle=max(0, expected),
        lead_to_demo_rate=avg_lead_to_demo,
        demo_to_application_rate=avg_demo_to_app,
        application_to_seat_rate=avg_app_to_seat,
        confidence=confidence,
    )


def cohort_pressure(points: Iterable[EnrollmentPoint], seat_target: int) -> float:
    rows = list(points)
    confirmed = sum(max(0, item.seats_confirmed) for item in rows)
    if seat_target <= 0:
        return 0.0
    return round((confirmed / seat_target) * 100.0, 2)
