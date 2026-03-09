from __future__ import annotations

from utils.retention_signal import (
    RetentionInput,
    evaluate_retention,
    explain_signal,
    intervention_heatmap,
    summarize_bands,
)


def test_f2p_1041_retention_signal_marks_critical_learners() -> None:
    signal = evaluate_retention(
        RetentionInput(
            learner_id="l1",
            attendance_percent=52,
            assignment_completion_percent=48,
            quiz_average=44,
            mentor_response_sla_percent=60,
        )
    )

    assert signal.band == "at_risk"
    assert "mentor-escalation" in signal.interventions


def test_f2p_1042_band_summary_and_heatmap_reflect_interventions() -> None:
    signals = [
        evaluate_retention(
            RetentionInput("l1", 52, 48, 44, 60),
        ),
        evaluate_retention(
            RetentionInput("l2", 84, 77, 70, 82),
        ),
        evaluate_retention(
            RetentionInput("l3", 72, 68, 65, 75),
        ),
    ]

    summary = summarize_bands(signals)
    heatmap = intervention_heatmap(signals)

    assert sum(summary.values()) == 3
    assert summary["at_risk"] >= 1
    assert heatmap["assignment-catchup-sprint"] >= 1


def test_f2p_1043_signal_explainer_returns_expected_shape() -> None:
    signal = evaluate_retention(
        RetentionInput("l4", 90, 88, 86, 92),
    )

    payload = explain_signal(signal)

    assert payload["learner_id"] == "l4"
    assert payload["requires_intervention"] is False
    assert isinstance(payload["interventions"], list)
