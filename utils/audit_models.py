"""Django model for database-backed audit log storage.

Provides an AuditLog model for persistent storage of audit entries
with efficient querying and indexing.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional, Union

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Index

from utils.audit_logger import (
    AuditAction,
    AuditContext,
    AuditEntry,
    AuditLevel,
    AuditStorage,
    FieldChange,
    InMemoryAuditStorage,
)


class AuditLogQuerySet(models.QuerySet):
    """Custom queryset with filtering utilities."""

    def by_entity(self, entity_type: str, entity_id: Optional[Union[int, str]] = None) -> AuditLogQuerySet:
        """Filter by entity type and optional ID."""
        qs = self.filter(entity_type=entity_type)
        if entity_id is not None:
            qs = qs.filter(entity_id=str(entity_id))
        return qs

    def by_user(self, user_id: int) -> AuditLogQuerySet:
        """Filter by user ID."""
        return self.filter(user_id=user_id)

    def by_action(self, action: Union[AuditAction, str]) -> AuditLogQuerySet:
        """Filter by action type."""
        action_value = action.value if isinstance(action, AuditAction) else action
        return self.filter(action=action_value)

    def by_time_range(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> AuditLogQuerySet:
        """Filter by time range."""
        qs = self
        if start:
            qs = qs.filter(timestamp__gte=start)
        if end:
            qs = qs.filter(timestamp__lte=end)
        return qs

    def significant_changes(self) -> AuditLogQuerySet:
        """Filter entries with actual changes (excludes no-op updates)."""
        return self.filter(has_changes=True)

    def recent(self, limit: int = 100) -> list["AuditLog"]:
        """Get recent entries."""
        return list(self.order_by("-timestamp")[:limit])


class AuditLogManager(models.Manager):
    """Custom manager with audit-specific methods."""

    def get_queryset(self) -> AuditLogQuerySet:
        return AuditLogQuerySet(self.model, using=self._db)

    def create_from_entry(self, entry: AuditEntry) -> "AuditLog":
        """Create AuditLog record from AuditEntry."""
        return self.create(
            id=entry.id,
            timestamp=entry.timestamp,
            action=entry.action.value,
            level=entry.level.value,
            entity_type=entry.entity_type,
            entity_id=str(entry.entity_id) if entry.entity_id is not None else None,
            entity_repr=entry.entity_repr,
            user_id=entry.context.user_id,
            user_email=entry.context.user_email,
            user_name=entry.context.user_name,
            ip_address=entry.context.ip_address,
            user_agent=entry.context.user_agent,
            request_id=entry.context.request_id,
            session_id=entry.context.session_id,
            correlation_id=entry.context.correlation_id,
            changes_data=[c.to_dict() for c in entry.changes],
            old_state=entry.old_state,
            new_state=entry.new_state,
            metadata=entry.metadata,
            duration_ms=entry.duration_ms,
            has_changes=len(entry.changes) > 0 or entry.action in [
                AuditAction.CREATE,
                AuditAction.DELETE,
            ],
        )

    def get_entity_history(
        self,
        entity_type: str,
        entity_id: Union[int, str],
        limit: int = 50,
    ) -> list["AuditLog"]:
        """Get audit history for a specific entity."""
        return (
            self.filter(entity_type=entity_type, entity_id=str(entity_id))
            .order_by("-timestamp")
            [:limit]
        )

    def get_user_activity(
        self,
        user_id: int,
        start_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list["AuditLog"]:
        """Get activity for a specific user."""
        qs = self.filter(user_id=user_id)
        if start_time:
            qs = qs.filter(timestamp__gte=start_time)
        return list(qs.order_by("-timestamp")[:limit])

    def get_change_summary(
        self,
        entity_type: str,
        entity_id: Union[int, str],
    ) -> dict[str, Any]:
        """Get summary of changes for an entity."""
        entries = self.filter(
            entity_type=entity_type,
            entity_id=str(entity_id),
        ).order_by("timestamp")

        return {
            "total_entries": entries.count(),
            "created_at": entries.filter(action=AuditAction.CREATE.value).first(),
            "last_updated": entries.filter(action=AuditAction.UPDATE.value).last(),
            "deleted_at": entries.filter(action=AuditAction.DELETE.value).first(),
            "unique_users": list(entries.values_list("user_id", flat=True).distinct()),
        }


class AuditLog(models.Model):
    """Database model for storing audit log entries.
    
    This model provides persistent storage for audit entries with
    efficient indexing for common query patterns.
    
    Attributes:
        id: UUID primary key
        timestamp: When the action occurred
        action: Type of action (create, update, delete, etc.)
        level: Severity level (info, warning, error, critical)
        entity_type: Model class name or entity type
        entity_id: Primary key of affected entity (stored as string for flexibility)
        entity_repr: Human-readable representation
        user_id: ID of user who performed action
        user_email: Email of user
        user_name: Full name of user
        ip_address: Client IP address
        user_agent: Client user agent
        request_id: Unique request identifier
        session_id: Session identifier
        correlation_id: Correlation ID for distributed tracing
        changes_data: JSON array of field changes
        old_state: Full serialized old state
        new_state: Full serialized new state
        metadata: Additional custom metadata
        duration_ms: Operation duration
        has_changes: Whether entry has meaningful changes
        created_at: When the log entry was created
    """

    # Primary identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(default=lambda: datetime.now(timezone.utc), db_index=True)

    # Action classification
    action = models.CharField(max_length=50, db_index=True, choices=[
        (a.value, a.name) for a in AuditAction
    ])
    level = models.CharField(max_length=20, default=AuditLevel.INFO.value, choices=[
        (l.value, l.name) for l in AuditLevel
    ])

    # Entity identification
    entity_type = models.CharField(max_length=100, db_index=True)
    entity_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    entity_repr = models.CharField(max_length=255, blank=True)

    # User context
    user_id = models.IntegerField(null=True, blank=True, db_index=True)
    user_email = models.EmailField(max_length=255, blank=True)
    user_name = models.CharField(max_length=255, blank=True)

    # Request context
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    request_id = models.CharField(max_length=100, blank=True, db_index=True)
    session_id = models.CharField(max_length=100, blank=True, db_index=True)
    correlation_id = models.CharField(max_length=100, blank=True, db_index=True)

    # Change data
    changes_data = models.JSONField(default=list, blank=True)
    old_state = models.JSONField(null=True, blank=True)
    new_state = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    duration_ms = models.FloatField(null=True, blank=True)
    has_changes = models.BooleanField(default=False, db_index=True)

    # System fields
    created_at = models.DateTimeField(auto_now_add=True)

    # Custom manager
    objects = AuditLogManager()

    class Meta:
        """Model metadata."""
        # This model lives in `utils/` and is used by lightweight evaluators/tests.
        # Declaring an explicit label lets Django load it without requiring `utils`
        # to be a full installed app.
        app_label = "utils"
        ordering = ["-timestamp"]
        indexes = [
            Index(fields=["entity_type", "entity_id", "-timestamp"]),
            Index(fields=["user_id", "-timestamp"]),
            Index(fields=["action", "-timestamp"]),
            Index(fields=["timestamp", "level"]),
            Index(fields=["request_id"]),
            Index(fields=["correlation_id"]),
            Index(fields=["entity_type", "action", "-timestamp"]),
        ]
        verbose_name = "Audit Log Entry"
        verbose_name_plural = "Audit Log Entries"

    def __str__(self) -> str:
        """String representation."""
        return f"{self.action} {self.entity_type}({self.entity_id}) by {self.user_email or 'unknown'} at {self.timestamp}"

    def to_audit_entry(self) -> AuditEntry:
        """Convert database record to AuditEntry dataclass."""
        return AuditEntry(
            id=str(self.id),
            timestamp=self.timestamp,
            action=AuditAction(self.action),
            level=AuditLevel(self.level),
            entity_type=self.entity_type,
            entity_id=self.entity_id,
            entity_repr=self.entity_repr,
            context=AuditContext(
                user_id=self.user_id,
                user_email=self.user_email,
                user_name=self.user_name,
                ip_address=self.ip_address,
                user_agent=self.user_agent,
                request_id=self.request_id,
                session_id=self.session_id,
                correlation_id=self.correlation_id,
            ),
            changes=[FieldChange(**c) for c in self.changes_data],
            old_state=self.old_state,
            new_state=self.new_state,
            metadata=self.metadata,
            duration_ms=self.duration_ms,
        )

    def get_changes_summary(self) -> str:
        """Get human-readable summary of changes."""
        if not self.changes_data:
            return "No field changes recorded"
        return ", ".join(
            f"{c['field_name']}: {c.get('old_value', 'N/A')} -> {c.get('new_value', 'N/A')}"
            for c in self.changes_data[:5]
        ) + ("..." if len(self.changes_data) > 5 else "")

    @property
    def is_create(self) -> bool:
        """Check if this is a create action."""
        return self.action == AuditAction.CREATE.value

    @property
    def is_update(self) -> bool:
        """Check if this is an update action."""
        return self.action == AuditAction.UPDATE.value

    @property
    def is_delete(self) -> bool:
        """Check if this is a delete action."""
        return self.action == AuditAction.DELETE.value


class DjangoAuditStorage(AuditStorage):
    """Django ORM-based storage backend for audit entries."""

    def store(self, entry: AuditEntry) -> str:
        """Store an audit entry in the database."""
        log = AuditLog.objects.create_from_entry(entry)
        return str(log.id)

    def query(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[Union[int, str]] = None,
        action: Optional[AuditAction] = None,
        user_id: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[AuditEntry]:
        """Query audit entries from database."""
        qs = AuditLog.objects.all()

        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        if entity_id is not None:
            qs = qs.filter(entity_id=str(entity_id))
        if action:
            qs = qs.filter(action=action.value)
        if user_id is not None:
            qs = qs.filter(user_id=user_id)
        if start_time:
            qs = qs.filter(timestamp__gte=start_time)
        if end_time:
            qs = qs.filter(timestamp__lte=end_time)

        return [log.to_audit_entry() for log in qs.order_by("-timestamp")[:limit]]

    def get_stats(self, days: int = 30) -> dict[str, Any]:
        """Get audit log statistics."""
        from django.db.models import Count
        from django.utils import timezone as django_tz

        cutoff = django_tz.now() - __import__("datetime").timedelta(days=days)

        recent = AuditLog.objects.filter(timestamp__gte=cutoff)

        return {
            "total_entries": recent.count(),
            "by_action": dict(
                recent.values("action").annotate(count=Count("id")).values_list("action", "count")
            ),
            "by_level": dict(
                recent.values("level").annotate(count=Count("id")).values_list("level", "count")
            ),
            "by_entity_type": dict(
                recent.values("entity_type")
                .annotate(count=Count("id"))
                .values_list("entity_type", "count")
            ),
            "unique_users": recent.filter(user_id__isnull=False).values("user_id").distinct().count(),
            "date_range": {
                "oldest": recent.order_by("timestamp").first().timestamp if recent.exists() else None,
                "newest": recent.order_by("-timestamp").first().timestamp if recent.exists() else None,
            },
        }


def get_django_storage() -> DjangoAuditStorage:
    """Factory function to get Django storage instance."""
    return DjangoAuditStorage()
