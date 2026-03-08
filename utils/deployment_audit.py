"""Deployment audit helpers for enterprise release operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class DeploymentAuditEvent:
    event_type: str
    actor: str
    service: str
    status: str
    timestamp_utc: str
    metadata: Dict[str, object]


@dataclass(frozen=True)
class DeploymentAuditSummary:
    total_events: int
    success_count: int
    failed_count: int
    rollback_count: int
    actor_counts: Dict[str, int]
    service_counts: Dict[str, int]


def _normalize_status(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"ok", "success", "succeeded"}:
        return "success"
    if normalized in {"rollback", "rolled_back", "reverted"}:
        return "rollback"
    if normalized in {"failed", "error", "failure"}:
        return "failed"
    return "unknown"


def build_audit_event(
    event_type: str,
    actor: str,
    service: str,
    status: str,
    metadata: Dict[str, object] | None = None,
    timestamp_utc: str | None = None,
) -> DeploymentAuditEvent:
    stamp = timestamp_utc or datetime.now(timezone.utc).isoformat()

    return DeploymentAuditEvent(
        event_type=event_type.strip().lower(),
        actor=actor.strip(),
        service=service.strip(),
        status=_normalize_status(status),
        timestamp_utc=stamp,
        metadata=dict(metadata or {}),
    )


def summarize_audit_events(events: Iterable[DeploymentAuditEvent]) -> DeploymentAuditSummary:
    actor_counts: Dict[str, int] = {}
    service_counts: Dict[str, int] = {}

    success_count = 0
    failed_count = 0
    rollback_count = 0
    total_events = 0

    for event in events:
        total_events += 1
        actor_counts[event.actor] = actor_counts.get(event.actor, 0) + 1
        service_counts[event.service] = service_counts.get(event.service, 0) + 1

        if event.status == "success":
            success_count += 1
        elif event.status == "failed":
            failed_count += 1
        elif event.status == "rollback":
            rollback_count += 1

    return DeploymentAuditSummary(
        total_events=total_events,
        success_count=success_count,
        failed_count=failed_count,
        rollback_count=rollback_count,
        actor_counts=actor_counts,
        service_counts=service_counts,
    )


def audit_health_score(summary: DeploymentAuditSummary) -> int:
    if summary.total_events == 0:
        return 100

    score = 100
    score -= summary.failed_count * 20
    score -= summary.rollback_count * 10
    if summary.success_count == 0 and summary.total_events > 0:
        score -= 30

    return max(0, score)


def to_lines(events: Iterable[DeploymentAuditEvent]) -> List[str]:
    lines: List[str] = []

    for event in events:
        lines.append(
            f"[{event.timestamp_utc}] {event.event_type} "
            f"service={event.service} actor={event.actor} status={event.status}"
        )

    return lines
