"""Proctoring risk scoring helpers for enterprise exam integrity workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ProctoringEvent:
    learner_id: str
    event_type: str
    severity: str
    confidence: float


@dataclass(frozen=True)
class ProctoringRiskReport:
    learner_id: str
    score: int
    level: str
    reasons: List[str]


SEVERITY_WEIGHT = {
    "info": 1,
    "warning": 3,
    "error": 7,
    "critical": 12,
}


def _normalize_severity(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in SEVERITY_WEIGHT:
        return normalized
    return "warning"


def _normalize_confidence(value: float) -> float:
    if value < 0:
        return 0.0
    if value > 1:
        return 1.0
    return float(value)


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 25:
        return "medium"
    return "low"


def build_proctoring_risk_report(learner_id: str, events: Iterable[ProctoringEvent]) -> ProctoringRiskReport:
    score = 0
    reasons: List[str] = []

    for event in events:
        severity = _normalize_severity(event.severity)
        confidence = _normalize_confidence(event.confidence)

        weighted = int(round(SEVERITY_WEIGHT[severity] * confidence * 4))
        score += weighted

        if weighted >= 8:
            reasons.append(f"{event.event_type}:{severity}")

    score = max(0, min(100, score))

    return ProctoringRiskReport(
        learner_id=learner_id,
        score=score,
        level=_risk_level(score),
        reasons=reasons,
    )


def summarize_risk_levels(reports: Iterable[ProctoringRiskReport]) -> Dict[str, int]:
    summary = {"low": 0, "medium": 0, "high": 0, "critical": 0}

    for report in reports:
        summary[report.level] = summary.get(report.level, 0) + 1

    return summary
