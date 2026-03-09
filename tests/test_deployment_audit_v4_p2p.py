from __future__ import annotations

from utils.deployment_audit import audit_health_score, build_audit_event, summarize_audit_events, to_lines


def test_p2p_405_deployment_audit_rolls_up_counts_correctly() -> None:
    summary = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "alice", "api", "failed"),
            build_audit_event("rollback", "bob", "api", "rollback"),
        ]
    )

    assert summary.total_events == 3
    assert summary.failed_count == 1
    assert summary.rollback_count == 1


def test_p2p_406_deployment_health_score_compares_healthy_and_noisy_profiles() -> None:
    healthy = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "bob", "worker", "success"),
        ]
    )
    noisy = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "failed"),
            build_audit_event("rollback", "alice", "api", "rollback"),
        ]
    )

    assert audit_health_score(healthy) > audit_health_score(noisy)


def test_p2p_407_deployment_audit_lines_include_structured_attributes() -> None:
    lines = to_lines(
        [
            build_audit_event("deploy", "alice", "api", "success", timestamp_utc="2026-03-20T08:00:00Z")
        ]
    )

    assert len(lines) == 1
    assert "service=api" in lines[0]
    assert "actor=alice" in lines[0]
