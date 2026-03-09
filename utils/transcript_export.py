from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List

from utils.certification_readiness import CertificationDecision
from utils.hiring_signal import HiringSignal
from utils.portfolio_evidence import PortfolioSummary


@dataclass(frozen=True)
class TranscriptRow:
    learner_id: str
    certification_status: str
    certification_score: float
    portfolio_score: float
    portfolio_grade: str
    readiness_score: float
    readiness_tier: str
    issued_at_iso: str


def build_row(
    certification: CertificationDecision,
    portfolio: PortfolioSummary,
    readiness: HiringSignal,
) -> TranscriptRow:
    return TranscriptRow(
        learner_id=certification.learner_id,
        certification_status=certification.status,
        certification_score=certification.weighted_score,
        portfolio_score=portfolio.score,
        portfolio_grade=portfolio.grade,
        readiness_score=readiness.readiness_score,
        readiness_tier=readiness.tier,
        issued_at_iso=datetime.now(timezone.utc).isoformat(),
    )


def bundle_rows(rows: Iterable[TranscriptRow]) -> List[TranscriptRow]:
    return sorted(rows, key=lambda row: row.readiness_score, reverse=True)


def to_csv(rows: Iterable[TranscriptRow]) -> str:
    header = (
        "learnerId,certificationStatus,certificationScore,portfolioScore,"
        "portfolioGrade,readinessScore,readinessTier,issuedAtIso"
    )
    lines = [
        ",".join(
            [
                row.learner_id,
                row.certification_status,
                str(row.certification_score),
                str(row.portfolio_score),
                row.portfolio_grade,
                str(row.readiness_score),
                row.readiness_tier,
                row.issued_at_iso,
            ]
        )
        for row in rows
    ]
    return "\n".join([header, *lines])
