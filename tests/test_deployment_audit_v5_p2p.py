from __future__ import annotations

from utils.deployment_audit import audit_health_score, build_audit_event, summarize_audit_events, to_lines


def test_p2p_1031_deployment_audit_summary_and_health_score() -> None:
    events = [
        build_audit_event("deploy", "alice", "api", "success", {"release": "r1"}, "2026-03-10T06:00:00+00:00"),
        build_audit_event("deploy", "bob", "web", "failed", {"release": "r1"}, "2026-03-10T06:10:00+00:00"),
        build_audit_event("rollback", "alice", "web", "rollback", {"release": "r1"}, "2026-03-10T06:20:00+00:00"),
    ]

    summary = summarize_audit_events(events)
    score = audit_health_score(summary)

    assert summary.total_events == 3
    assert summary.success_count == 1
    assert summary.failed_count == 1
    assert summary.rollback_count == 1
    assert score == 70


def test_p2p_1032_audit_lines_contain_ordered_event_shape() -> None:
    events = [
        build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-10T06:00:00+00:00"),
        build_audit_event("deploy", "alice", "web", "success", timestamp_utc="2026-03-10T06:02:00+00:00"),
    ]

    lines = to_lines(events)

    assert len(lines) == 2
    assert "service=api" in lines[0]
    assert "status=success" in lines[1]
