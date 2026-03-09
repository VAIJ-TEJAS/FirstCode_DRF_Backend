from __future__ import annotations

from utils.proctoring_capacity import ProctorShift, evaluate_shift, intervention_queue, summarize_region


def test_f2p_1111_proctor_shift_detects_critical_load() -> None:
    signal = evaluate_shift(
        ProctorShift(
            shift_id="s1",
            region="india",
            proctor_count=10,
            active_sessions=59,
            queued_sessions=18,
        )
    )

    assert signal.status == "critical"
    assert "incident bridge" in signal.recommendation


def test_f2p_1112_region_summary_and_queue_prioritize_hotspots() -> None:
    shifts = [
        ProctorShift("s1", "india", 10, 59, 18),
        ProctorShift("s2", "india", 8, 30, 1),
        ProctorShift("s3", "emea", 6, 18, 0),
    ]

    summary = summarize_region(shifts)
    queue = intervention_queue(shifts)

    assert summary["india"] > summary["emea"]
    assert queue[0].shift_id == "s1"
