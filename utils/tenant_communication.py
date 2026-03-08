"""Tenant-facing release communication helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class TenantNotification:
    tenant_id: str
    channel: str
    template: str
    variables: Dict[str, str]


def build_tenant_notification(
    tenant_id: str,
    channel: str,
    template: str,
    variables: Dict[str, str] | None = None,
) -> TenantNotification:
    return TenantNotification(
        tenant_id=tenant_id,
        channel=channel,
        template=template,
        variables=dict(variables or {}),
    )


def validate_notifications(notifications: Iterable[TenantNotification]) -> List[str]:
    issues: List[str] = []

    for notification in notifications:
        if not notification.tenant_id:
            issues.append("Notification has empty tenant id.")

        if notification.channel not in {"email", "slack", "webhook"}:
            issues.append(f"Unsupported notification channel: {notification.channel}")

        if not notification.template:
            issues.append("Notification has empty template.")

    return issues


def group_by_channel(notifications: Iterable[TenantNotification]) -> Dict[str, List[TenantNotification]]:
    grouped: Dict[str, List[TenantNotification]] = {}

    for notification in notifications:
        grouped.setdefault(notification.channel, []).append(notification)

    return grouped


def render_preview(notification: TenantNotification) -> str:
    values = ", ".join(f"{key}={value}" for key, value in sorted(notification.variables.items()))
    return (
        f"tenant={notification.tenant_id} "
        f"channel={notification.channel} template={notification.template} vars=[{values}]"
    )
