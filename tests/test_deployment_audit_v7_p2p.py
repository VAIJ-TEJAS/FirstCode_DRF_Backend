from __future__ import annotations

from utils.deployment_audit import audit_health_score, build_audit_event, summarize_audit_events


def test_p2p_1631_deployment_audit_health_penalizes_failures() -> None:
    events = [
        build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-10T06:00:00+00:00"),
        build_audit_event("deploy", "bob", "web", "failed", timestamp_utc="2026-03-10T06:05:00+00:00"),
        build_audit_event("deploy", "bob", "worker", "success", timestamp_utc="2026-03-10T06:10:00+00:00"),
    ]

    summary = summarize_audit_events(events)

    assert summary.total_events == 3
    assert summary.failed_count == 1
    assert audit_health_score(summary) == 80


def test_p2p_1632_deployment_audit_health_is_full_on_success_only() -> None:
    events = [
        build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-10T06:00:00+00:00"),
        build_audit_event("deploy", "bob", "web", "success", timestamp_utc="2026-03-10T06:05:00+00:00"),
    ]

    summary = summarize_audit_events(events)
    assert audit_health_score(summary) == 100
