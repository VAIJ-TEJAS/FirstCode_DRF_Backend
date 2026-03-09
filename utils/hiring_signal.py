from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List

from utils.certification_readiness import CertificationDecision
from utils.portfolio_evidence import PortfolioSummary


@dataclass(frozen=True)
class HiringSignal:
    learner_id: str
    readiness_score: float
    tier: str
    blockers: List[str]
    recommendations: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _tier(score: float) -> str:
    if score >= 85:
        return "hire_ready"
    if score >= 70:
        return "almost_ready"
    if score >= 50:
        return "developing"
    return "high_risk"


def build_hiring_signal(
    learner_id: str,
    portfolio: PortfolioSummary,
    certification: CertificationDecision,
    mock_interview_score: float,
    attendance_rate: float,
) -> HiringSignal:
    blockers: List[str] = []
    recommendations: List[str] = []

    if certification.status != "eligible":
        blockers.append("certification-incomplete")
        recommendations.append("Complete pending certification modules")
    if portfolio.needs_review:
        blockers.append("portfolio-review-required")
        recommendations.append("Resolve portfolio verification and competency gaps")
    if mock_interview_score < 60:
        blockers.append("mock-interview-low")
        recommendations.append("Schedule interview coaching track")
    if attendance_rate < 75:
        blockers.append("attendance-risk")
        recommendations.append("Improve attendance consistency over next sprint")

    score = _clamp(
        portfolio.score * 0.35
        + mock_interview_score * 0.25
        + attendance_rate * 0.15
        + certification.weighted_score * 0.25
        - (len(blockers) * 6.0)
    )

    return HiringSignal(
        learner_id=learner_id,
        readiness_score=round(score, 2),
        tier=_tier(score),
        blockers=blockers,
        recommendations=recommendations,
    )


def summarize_tiers(signals: Iterable[HiringSignal]) -> Dict[str, int]:
    summary = {
        "hire_ready": 0,
        "almost_ready": 0,
        "developing": 0,
        "high_risk": 0,
    }
    for signal in signals:
        summary[signal.tier] += 1
    return summary
