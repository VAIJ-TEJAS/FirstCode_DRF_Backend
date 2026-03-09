from __future__ import annotations

from utils.portfolio_evidence import PortfolioArtifact, coverage_gaps, summarize_portfolio


def test_f2p_911_summary_scores_verified_portfolio() -> None:
    summary = summarize_portfolio(
        learner_id="learner-r1",
        artifacts=[
            PortfolioArtifact("a1", "react", 89, 80, True),
            PortfolioArtifact("a2", "typescript", 85, 75, True),
            PortfolioArtifact("a3", "testing", 92, 85, True),
        ],
    )

    assert summary.grade == "A"
    assert summary.needs_review is False
    assert sorted(summary.competency_coverage.keys()) == ["react", "testing", "typescript"]


def test_f2p_912_summary_marks_review_if_unverified() -> None:
    summary = summarize_portfolio(
        learner_id="learner-r2",
        artifacts=[PortfolioArtifact("a1", "react", 62, 50, False)],
    )

    assert summary.needs_review is True
    assert summary.grade in {"D", "F"}


def test_f2p_913_empty_portfolio_defaults_to_failing_review() -> None:
    summary = summarize_portfolio(learner_id="learner-r3", artifacts=[])

    assert summary.score == 0.0
    assert summary.grade == "F"
    assert summary.needs_review is True


def test_f2p_914_coverage_gaps_returns_missing_competencies() -> None:
    gaps = coverage_gaps(
        artifacts=[
            PortfolioArtifact("a1", "react", 89, 80, True),
            PortfolioArtifact("a2", "testing", 85, 75, True),
        ],
        required_competencies=["react", "typescript", "testing", "system-design"],
    )

    assert gaps == ["typescript", "system-design"]
