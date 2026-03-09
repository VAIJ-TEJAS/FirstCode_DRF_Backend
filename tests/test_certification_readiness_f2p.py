from __future__ import annotations

from utils.certification_readiness import (
    CertificationModule,
    CertificationTrack,
    evaluate_track,
    recommended_modules,
)


def _track() -> CertificationTrack:
    return CertificationTrack(
        track_id="track-fe",
        passing_score=80.0,
        modules=[
            CertificationModule(module_id="m1", required=True, weight=20),
            CertificationModule(module_id="m2", required=True, weight=40),
            CertificationModule(module_id="m3", required=False, weight=25),
            CertificationModule(module_id="m4", required=True, weight=15),
        ],
    )


def test_f2p_901_learner_eligible_on_full_completion() -> None:
    decision = evaluate_track(
        learner_id="learner-1",
        track=_track(),
        module_scores={"m1": 88, "m2": 90, "m3": 82, "m4": 85},
    )

    assert decision.status == "eligible"
    assert decision.completion_rate == 100.0
    assert decision.weighted_score >= 80.0
    assert decision.missing_required_modules == []


def test_f2p_902_missing_required_modules_are_reported() -> None:
    decision = evaluate_track(
        learner_id="learner-2",
        track=_track(),
        module_scores={"m1": 80},
    )

    assert decision.status == "in_progress"
    assert sorted(decision.missing_required_modules) == ["m2", "m4"]


def test_f2p_903_at_risk_when_low_score_after_half_completion() -> None:
    decision = evaluate_track(
        learner_id="learner-3",
        track=_track(),
        module_scores={"m1": 32, "m2": 40, "m3": 35},
    )

    assert decision.completion_rate == 75.0
    assert decision.weighted_score < 70.0
    assert decision.status == "at_risk"


def test_f2p_904_recommendation_queue_prioritizes_required() -> None:
    recs = recommended_modules(
        track=_track(),
        module_scores={"m1": 80},
        limit=2,
    )

    assert recs == ["m2", "m4"]
