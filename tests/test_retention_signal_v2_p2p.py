from __future__ import annotations

from utils.retention_signal import RetentionInput, evaluate_retention, intervention_heatmap, summarize_bands


def test_p2p_1131_retention_signals_generate_band_distribution() -> None:
    signals = [
        evaluate_retention(RetentionInput("l1", 92, 90, 88, 90)),
        evaluate_retention(RetentionInput("l2", 76, 72, 68, 70)),
        evaluate_retention(RetentionInput("l3", 60, 54, 49, 62)),
    ]

    summary = summarize_bands(signals)
    heatmap = intervention_heatmap(signals)

    assert sum(summary.values()) == 3
    assert summary["stable"] >= 1
    assert heatmap["assignment-catchup-sprint"] >= 1


def test_p2p_1132_retention_signal_interventions_cover_low_subscores() -> None:
    signal = evaluate_retention(RetentionInput("l4", 58, 52, 45, 64))

    assert signal.band in {"at_risk", "critical"}
    assert "attendance-recovery-plan" in signal.interventions
    assert "concept-remediation-bootcamp" in signal.interventions
