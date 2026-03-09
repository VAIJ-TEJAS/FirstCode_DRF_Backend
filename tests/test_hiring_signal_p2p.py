from __future__ import annotations

from utils.certification_readiness import CertificationModule, CertificationTrack, evaluate_track
from utils.hiring_signal import build_hiring_signal, summarize_tiers
from utils.portfolio_evidence import PortfolioArtifact, summarize_portfolio


def _track() -> CertificationTrack:
    return CertificationTrack(
        track_id="track-enterprise-fe",
        passing_score=82.0,
        modules=[
            CertificationModule("mod-a", True, 35),
            CertificationModule("mod-b", True, 25),
            CertificationModule("mod-c", True, 20),
            CertificationModule("mod-d", False, 20),
        ],
    )


def test_p2p_931_progression_from_at_risk_to_eligible_improves_readiness() -> None:
    before = evaluate_track(
        learner_id="learner-z",
        track=_track(),
        module_scores={"mod-a": 78, "mod-b": 81},
    )
    after = evaluate_track(
        learner_id="learner-z",
        track=_track(),
        module_scores={"mod-a": 86, "mod-b": 88, "mod-c": 84, "mod-d": 82},
    )

    portfolio = summarize_portfolio(
        learner_id="learner-z",
        artifacts=[
            PortfolioArtifact("x1", "react", 87, 84, True),
            PortfolioArtifact("x2", "design-system", 85, 80, True),
            PortfolioArtifact("x3", "testing", 88, 83, True),
        ],
    )

    signal_before = build_hiring_signal(
        learner_id="learner-z",
        portfolio=portfolio,
        certification=before,
        mock_interview_score=76,
        attendance_rate=84,
    )
    signal_after = build_hiring_signal(
        learner_id="learner-z",
        portfolio=portfolio,
        certification=after,
        mock_interview_score=76,
        attendance_rate=84,
    )

    assert before.status == "at_risk"
    assert after.status == "eligible"
    assert signal_after.readiness_score > signal_before.readiness_score


def test_p2p_932_tier_summary_counts_all_segments() -> None:
    signals = [
        build_hiring_signal(
            learner_id="l1",
            portfolio=summarize_portfolio("l1", [PortfolioArtifact("a1", "react", 95, 90, True), PortfolioArtifact("a2", "ts", 92, 88, True), PortfolioArtifact("a3", "test", 90, 86, True)]),
            certification=evaluate_track("l1", _track(), {"mod-a": 90, "mod-b": 88, "mod-c": 86, "mod-d": 84}),
            mock_interview_score=90,
            attendance_rate=95,
        ),
        build_hiring_signal(
            learner_id="l2",
            portfolio=summarize_portfolio("l2", [PortfolioArtifact("a1", "react", 74, 70, True), PortfolioArtifact("a2", "ts", 71, 68, True), PortfolioArtifact("a3", "test", 70, 65, True)]),
            certification=evaluate_track("l2", _track(), {"mod-a": 78, "mod-b": 77, "mod-c": 76}),
            mock_interview_score=72,
            attendance_rate=78,
        ),
        build_hiring_signal(
            learner_id="l3",
            portfolio=summarize_portfolio("l3", [PortfolioArtifact("a1", "react", 55, 50, False)]),
            certification=evaluate_track("l3", _track(), {"mod-a": 45, "mod-b": 40}),
            mock_interview_score=50,
            attendance_rate=60,
        ),
    ]

    summary = summarize_tiers(signals)

    assert sum(summary.values()) == 3
    assert summary["hire_ready"] == 1
    assert summary["high_risk"] >= 1
