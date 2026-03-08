from __future__ import annotations

from utils.deployment_audit import audit_health_score, build_audit_event, summarize_audit_events


def test_p2p_106_deployment_audit_matrix_all_success_has_top_score() -> None:
    summary = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "bob", "web", "success"),
            build_audit_event("deploy", "charlie", "worker", "success"),
        ]
    )

    assert audit_health_score(summary) == 100


def test_p2p_107_deployment_audit_matrix_failed_release_reduces_score() -> None:
    healthy = summarize_audit_events([build_audit_event("deploy", "alice", "api", "success")])
    failed = summarize_audit_events([build_audit_event("deploy", "alice", "api", "failed")])

    assert audit_health_score(failed) < audit_health_score(healthy)


def test_p2p_108_deployment_audit_matrix_rollback_reduces_score_less_than_failure() -> None:
    failed = summarize_audit_events([build_audit_event("deploy", "alice", "api", "failed")])
    rollback = summarize_audit_events([build_audit_event("rollback", "alice", "api", "rollback")])

    assert audit_health_score(rollback) > audit_health_score(failed)


def test_p2p_109_deployment_audit_matrix_actor_counts_accumulate_correctly() -> None:
    summary = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "alice", "web", "success"),
            build_audit_event("deploy", "bob", "worker", "success"),
        ]
    )

    assert summary.actor_counts["alice"] == 2
    assert summary.actor_counts["bob"] == 1


def test_p2p_110_deployment_audit_matrix_service_counts_accumulate_correctly() -> None:
    summary = summarize_audit_events(
        [
            build_audit_event("deploy", "alice", "api", "success"),
            build_audit_event("deploy", "bob", "api", "success"),
            build_audit_event("deploy", "charlie", "worker", "success"),
        ]
    )

    assert summary.service_counts["api"] == 2
    assert summary.service_counts["worker"] == 1
