from __future__ import annotations

from utils.deployment_audit import audit_health_score, build_audit_event, summarize_audit_events, to_lines


def test_p2p_206_deployment_audit_summary_counts_event_types() -> None:
    summary = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "bob", "worker", "failed"),
            build_audit_event("rollback", "alice", "api", "rollback"),
        ]
    )

    assert summary.total_events == 3
    assert summary.success_count == 1
    assert summary.failed_count == 1
    assert summary.rollback_count == 1


def test_p2p_207_deployment_audit_health_score_compares_profiles() -> None:
    healthy = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "alice", "web", "success"),
        ]
    )
    noisy = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "failed"),
            build_audit_event("rollback", "alice", "api", "rollback"),
        ]
    )

    assert audit_health_score(healthy) > audit_health_score(noisy)


def test_p2p_208_deployment_audit_lines_are_human_readable() -> None:
    lines = to_lines(
        [
            build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-12T08:00:00Z")
        ]
    )

    assert len(lines) == 1
    assert "service=api" in lines[0]
    assert "status=success" in lines[0]


def test_p2p_209_deployment_actor_and_service_counts_stay_consistent() -> None:
    summary = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "bob", "worker", "success"),
        ]
    )

    assert summary.actor_counts["alice"] == 2
    assert summary.service_counts["api"] == 2
