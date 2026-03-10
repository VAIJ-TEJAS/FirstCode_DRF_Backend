from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualitySignal:
    cohort_id: str
    assessments: int
    avg_score: float
    remediation_rate: float


def build_quality_scorecard(signal: QualitySignal) -> dict:
    if signal.assessments <= 0:
        score_factor = 0
    else:
        score_factor = signal.avg_score / 100

    remediation_penalty = min(signal.remediation_rate * 0.5, 0.4)
    quality_index = round(max(score_factor - remediation_penalty, 0), 2)

    if quality_index < 0.65:
        risk_band = "high"
    elif quality_index < 0.8:
        risk_band = "medium"
    else:
        risk_band = "low"

    return {"cohort_id": signal.cohort_id, "quality_index": quality_index, "risk_band": risk_band}
