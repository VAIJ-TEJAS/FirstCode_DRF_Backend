from __future__ import annotations

from utils.deployment_audit import (
    audit_health_score,
    build_audit_event,
    summarize_audit_events,
    to_lines,
)


def test_p2p_017_audit_summary_counts_success_failure_and_rollback() -> None:
    events = [
        build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-09T06:00:00Z"),
        build_audit_event("deploy", "bob", "worker", "failed", timestamp_utc="2026-03-09T06:10:00Z"),
        build_audit_event("rollback", "alice", "api", "rollback", timestamp_utc="2026-03-09T06:15:00Z"),
    ]

    summary = summarize_audit_events(events)

    assert summary.total_events == 3
    assert summary.success_count == 1
    assert summary.failed_count == 1
    assert summary.rollback_count == 1


def test_p2p_018_audit_summary_tracks_actor_and_service_distribution() -> None:
    events = [
        build_audit_event("deploy", "alice", "api", "success"),
        build_audit_event("deploy", "alice", "api", "success"),
        build_audit_event("deploy", "charlie", "web", "success"),
    ]

    summary = summarize_audit_events(events)

    assert summary.actor_counts["alice"] == 2
    assert summary.service_counts["api"] == 2


def test_p2p_019_audit_health_score_drops_for_failures_and_rollbacks() -> None:
    healthy = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "alice", "worker", "success"),
        ]
    )

    noisy = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "failed"),
            build_audit_event("rollback", "alice", "api", "rollback"),
        ]
    )

    assert audit_health_score(healthy) > audit_health_score(noisy)


def test_p2p_020_to_lines_produces_readable_log_strings() -> None:
    lines = to_lines(
        [
            build_audit_event(
                "deploy",
                "alice",
                "api",
                "success",
                timestamp_utc="2026-03-09T06:00:00Z",
            )
        ]
    )

    assert len(lines) == 1
    assert "service=api" in lines[0]
    assert "status=success" in lines[0]


def test_p2p_021_unknown_status_is_normalized_but_preserved_as_non_success() -> None:
    event = build_audit_event("deploy", "alice", "api", "mystery-status")
    summary = summarize_audit_events([event])

    assert event.status == "unknown"
    assert summary.success_count == 0


def test_p2p_022_empty_event_stream_is_scored_as_healthy_baseline() -> None:
    summary = summarize_audit_events([])

    assert summary.total_events == 0
    assert audit_health_score(summary) == 100
