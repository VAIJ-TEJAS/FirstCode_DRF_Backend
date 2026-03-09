from __future__ import annotations

from utils.deployment_audit import audit_health_score, build_audit_event, summarize_audit_events, to_lines


def test_p2p_305_audit_events_roll_up_actor_and_service_counts() -> None:
    summary = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "alice", "worker", "success"),
            build_audit_event("deploy", "bob", "api", "failed"),
        ]
    )

    assert summary.actor_counts["alice"] == 2
    assert summary.service_counts["api"] == 2


def test_p2p_306_audit_health_score_penalizes_failures() -> None:
    good = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "alice", "worker", "success"),
        ]
    )
    bad = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "failed"),
            build_audit_event("rollback", "alice", "api", "rollback"),
        ]
    )

    assert audit_health_score(good) > audit_health_score(bad)


def test_p2p_307_audit_lines_include_structured_fields() -> None:
    lines = to_lines(
        [
            build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-15T08:00:00Z")
        ]
    )

    assert len(lines) == 1
    assert "service=api" in lines[0]
    assert "actor=alice" in lines[0]
    assert "status=success" in lines[0]
