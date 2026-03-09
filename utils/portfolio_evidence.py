from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class PortfolioArtifact:
    artifact_id: str
    competency: str
    rubric_score: float
    reviewer_confidence: float
    verified: bool


@dataclass(frozen=True)
class PortfolioSummary:
    learner_id: str
    score: float
    grade: str
    competency_coverage: Dict[str, int]
    needs_review: bool


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def summarize_portfolio(learner_id: str, artifacts: Iterable[PortfolioArtifact]) -> PortfolioSummary:
    artifact_list = list(artifacts)
    if not artifact_list:
        return PortfolioSummary(
            learner_id=learner_id,
            score=0.0,
            grade="F",
            competency_coverage={},
            needs_review=True,
        )

    coverage: Dict[str, int] = {}
    total = 0.0

    for artifact in artifact_list:
        coverage[artifact.competency] = coverage.get(artifact.competency, 0) + 1
        confidence_boost = artifact.reviewer_confidence * 0.2
        verification_penalty = 0.0 if artifact.verified else 12.0
        total += _clamp(artifact.rubric_score + confidence_boost - verification_penalty)

    score = round(total / len(artifact_list), 2)
    needs_review = any(not artifact.verified for artifact in artifact_list) or len(coverage) < 3

    return PortfolioSummary(
        learner_id=learner_id,
        score=score,
        grade=_grade(score),
        competency_coverage=coverage,
        needs_review=needs_review,
    )


def coverage_gaps(artifacts: Iterable[PortfolioArtifact], required_competencies: Iterable[str]) -> List[str]:
    covered = {artifact.competency for artifact in artifacts}
    return [competency for competency in required_competencies if competency not in covered]
