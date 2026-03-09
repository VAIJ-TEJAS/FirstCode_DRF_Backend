from __future__ import annotations

from utils.deployment_audit import audit_health_score, build_audit_event, summarize_audit_events


def test_p2p_1321_audit_health_drops_with_failed_and_rollback_events() -> None:
    events = [
        build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-10T06:00:00+00:00"),
        build_audit_event("deploy", "bob", "web", "failed", timestamp_utc="2026-03-10T06:05:00+00:00"),
        build_audit_event("rollback", "alice", "web", "rollback", timestamp_utc="2026-03-10T06:06:00+00:00"),
        build_audit_event("deploy", "alice", "worker", "success", timestamp_utc="2026-03-10T06:10:00+00:00"),
    ]

    summary = summarize_audit_events(events)

    assert summary.total_events == 4
    assert summary.failed_count == 1
    assert summary.rollback_count == 1
    assert audit_health_score(summary) == 70


def test_p2p_1322_audit_health_is_max_for_empty_event_stream() -> None:
    summary = summarize_audit_events([])
    assert audit_health_score(summary) == 100
