from __future__ import annotations

from utils.certification_readiness import CertificationDecision
from utils.hiring_signal import HiringSignal
from utils.portfolio_evidence import PortfolioSummary
from utils.transcript_export import build_row, bundle_rows, to_csv


def _row(learner_id: str, readiness_score: float, tier: str) -> tuple[CertificationDecision, PortfolioSummary, HiringSignal]:
    certification = CertificationDecision(
        learner_id=learner_id,
        track_id="track1",
        status="eligible",
        weighted_score=88.0,
        completion_rate=100.0,
        missing_required_modules=[],
    )
    portfolio = PortfolioSummary(
        learner_id=learner_id,
        score=90.0,
        grade="A",
        competency_coverage={"react": 2, "testing": 2, "system": 1},
        needs_review=False,
    )
    readiness = HiringSignal(
        learner_id=learner_id,
        readiness_score=readiness_score,
        tier=tier,
        blockers=[],
        recommendations=[],
    )
    return certification, portfolio, readiness


def test_p2p_941_bundle_rows_sorted_by_readiness_score() -> None:
    c1, p1, r1 = _row("l1", 90.0, "hire_ready")
    c2, p2, r2 = _row("l2", 70.0, "almost_ready")

    rows = bundle_rows([build_row(c2, p2, r2), build_row(c1, p1, r1)])

    assert rows[0].learner_id == "l1"
    assert rows[1].learner_id == "l2"


def test_p2p_942_csv_contains_header_and_rows() -> None:
    c1, p1, r1 = _row("l1", 90.0, "hire_ready")
    c2, p2, r2 = _row("l2", 70.0, "almost_ready")
    rows = bundle_rows([build_row(c1, p1, r1), build_row(c2, p2, r2)])

    csv_output = to_csv(rows)
    lines = csv_output.splitlines()

    assert lines[0].startswith("learnerId,certificationStatus")
    assert len(lines) == 3
    assert "l1" in lines[1] or "l1" in lines[2]
