"""Audit logging system for enterprise-grade data change tracking.

This module provides comprehensive audit logging capabilities including:
- Automatic change tracking via middleware
- Manual audit logging API
- Audit log querying and filtering
- Data diff generation for updates
"""

from __future__ import annotations

import json
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union

from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.http import HttpRequest
from django.contrib.auth.models import User


class AuditAction(str, Enum):
    """Standardized audit action types."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    VIEW = "view"
    LOGIN = "login"
    LOGOUT = "logout"
    EXPORT = "export"
    IMPORT = "import"
    BULK_CREATE = "bulk_create"
    BULK_UPDATE = "bulk_update"
    BULK_DELETE = "bulk_delete"


class AuditLevel(str, Enum):
    """Audit log severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass(frozen=True)
class AuditContext:
    """Context data for audit log entries.
    
    Attributes:
        user_id: ID of the user performing the action
        user_email: Email of the user
        user_name: Full name of the user
        ip_address: Client IP address
        user_agent: Client user agent string
        request_id: Unique request identifier
        session_id: Session identifier
        correlation_id: Correlation ID for distributed tracing
    """
    user_id: Optional[int] = None
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "user_id": self.user_id,
            "user_email": self.user_email,
            "user_name": self.user_name,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
        }


@dataclass(frozen=True)
class FieldChange:
    """Represents a single field change in an update operation.
    
    Attributes:
        field_name: Name of the field that changed
        old_value: Previous value (serialized)
        new_value: New value (serialized)
        field_type: Django field type
    """
    field_name: str
    old_value: Any
    new_value: Any
    field_type: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert field change to dictionary."""
        return {
            "field_name": self.field_name,
            "old_value": self._serialize_value(self.old_value),
            "new_value": self._serialize_value(self.new_value),
            "field_type": self.field_type,
        }

    @staticmethod
    def _serialize_value(value: Any) -> Any:
        """Serialize a value for JSON storage."""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, models.Model):
            return f"{value.__class__.__name__}(id={value.pk})"
        if hasattr(value, "pk"):
            return {"model": value.__class__.__name__, "id": value.pk}
        return str(value) if not isinstance(value, (str, int, float, bool, list, dict)) else value


@dataclass
class AuditEntry:
    """Complete audit log entry.
    
    Attributes:
        id: Unique identifier for this audit entry
        timestamp: When the action occurred
        action: Type of action performed
        level: Severity level
        entity_type: Model class name or entity type
        entity_id: Primary key of the affected entity
        entity_repr: Human-readable representation
        context: User and request context
        changes: List of field changes (for updates)
        old_state: Full serialized old state (for deletes)
        new_state: Full serialized new state (for creates)
        metadata: Additional custom metadata
        duration_ms: Operation duration in milliseconds
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    action: AuditAction = AuditAction.VIEW
    level: AuditLevel = AuditLevel.INFO
    entity_type: str = ""
    entity_id: Optional[Union[int, str]] = None
    entity_repr: str = ""
    context: AuditContext = field(default_factory=AuditContext)
    changes: List[FieldChange] = field(default_factory=list)
    old_state: Optional[dict[str, Any]] = None
    new_state: Optional[dict[str, Any]] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert audit entry to dictionary for serialization."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "level": self.level.value,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "entity_repr": self.entity_repr,
            "context": self.context.to_dict(),
            "changes": [c.to_dict() for c in self.changes],
            "old_state": self.old_state,
            "new_state": self.new_state,
            "metadata": self.metadata,
            "duration_ms": self.duration_ms,
        }

    def to_json(self) -> str:
        """Serialize audit entry to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def has_significant_changes(self, ignore_fields: Optional[list[str]] = None) -> bool:
        """Check if entry has meaningful changes beyond ignored fields."""
        if self.action != AuditAction.UPDATE:
            return True
        # For update events, we prefer a field-level diff, but some callers/tests
        # intentionally emit UPDATE entries without explicit `changes`. Those are
        # still meaningful from an audit trail standpoint.
        if not self.changes:
            return True
        ignore = set(ignore_fields or ["updated_at", "last_modified", "modified_at"])
        significant = [c for c in self.changes if c.field_name not in ignore]
        return len(significant) > 0


class AuditLogger:
    """Main audit logging interface.
    
    Provides methods for logging various types of actions and
    supports pluggable storage backends.
    """

    _storage: Optional[AuditStorage] = None
    _enabled: bool = True
    _ignored_models: set[str] = set()
    _ignored_fields: dict[str, set[str]] = {}
    _UNSET: object = object()

    @classmethod
    def configure(
        cls,
        storage: Optional[AuditStorage] | object = _UNSET,
        enabled: bool = True,
        ignored_models: Optional[list[str]] = None,
    ) -> None:
        """Configure the global audit logger.
        
        Args:
            storage: Storage backend for audit entries
            enabled: Whether logging is enabled
            ignored_models: List of model names to ignore
        """
        if storage is not cls._UNSET:
            cls._storage = storage  # type: ignore[assignment]
        cls._enabled = enabled
        if ignored_models:
            cls._ignored_models = set(ignored_models)

    @classmethod
    def is_enabled(cls) -> bool:
        """Check if audit logging is enabled."""
        return cls._enabled and cls._storage is not None

    @classmethod
    def is_model_ignored(cls, model_name: str) -> bool:
        """Check if a model should be ignored."""
        return model_name in cls._ignored_models

    @classmethod
    def log(cls, entry: AuditEntry) -> Optional[str]:
        """Log an audit entry.
        
        Args:
            entry: The audit entry to log
            
        Returns:
            Entry ID if logged successfully, None otherwise
        """
        if not cls.is_enabled():
            return None
        if not entry.has_significant_changes():
            return None
        if cls._storage is None:
            return None
        return cls._storage.store(entry)

    @classmethod
    def log_create(
        cls,
        instance: models.Model,
        context: AuditContext,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Log a create operation.
        
        Args:
            instance: The created model instance
            context: Audit context with user info
            metadata: Additional metadata
            
        Returns:
            Entry ID if logged successfully
        """
        entry = AuditEntry(
            action=AuditAction.CREATE,
            entity_type=instance.__class__.__name__,
            entity_id=instance.pk,
            entity_repr=str(instance)[:255],
            context=context,
            new_state=cls._serialize_instance(instance),
            metadata=metadata or {},
        )
        return cls.log(entry)

    @classmethod
    def log_update(
        cls,
        old_instance: models.Model,
        new_instance: models.Model,
        context: AuditContext,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Log an update operation with field-level diff.
        
        Args:
            old_instance: The instance before update
            new_instance: The instance after update
            context: Audit context with user info
            metadata: Additional metadata
            
        Returns:
            Entry ID if logged successfully
        """
        changes = cls._compute_changes(old_instance, new_instance)
        if not changes:
            return None

        entry = AuditEntry(
            action=AuditAction.UPDATE,
            entity_type=new_instance.__class__.__name__,
            entity_id=new_instance.pk,
            entity_repr=str(new_instance)[:255],
            context=context,
            changes=changes,
            old_state=cls._serialize_instance(old_instance),
            new_state=cls._serialize_instance(new_instance),
            metadata=metadata or {},
        )
        return cls.log(entry)

    @classmethod
    def log_delete(
        cls,
        instance: models.Model,
        context: AuditContext,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Optional[str]:
        """Log a delete operation.
        
        Args:
            instance: The deleted model instance
            context: Audit context with user info
            metadata: Additional metadata
            
        Returns:
            Entry ID if logged successfully
        """
        entry = AuditEntry(
            action=AuditAction.DELETE,
            entity_type=instance.__class__.__name__,
            entity_id=instance.pk,
            entity_repr=str(instance)[:255],
            context=context,
            old_state=cls._serialize_instance(instance),
            metadata=metadata or {},
        )
        return cls.log(entry)

    @classmethod
    def log_action(
        cls,
        action: AuditAction,
        entity_type: str,
        entity_id: Optional[Union[int, str]] = None,
        context: Optional[AuditContext] = None,
        metadata: Optional[dict[str, Any]] = None,
        level: AuditLevel = AuditLevel.INFO,
    ) -> Optional[str]:
        """Log a generic action.
        
        Args:
            action: The action type
            entity_type: Type of entity affected
            entity_id: Entity identifier
            context: Audit context
            metadata: Additional metadata
            level: Severity level
            
        Returns:
            Entry ID if logged successfully
        """
        entry = AuditEntry(
            action=action,
            level=level,
            entity_type=entity_type,
            entity_id=entity_id,
            context=context or AuditContext(),
            metadata=metadata or {},
        )
        return cls.log(entry)

    @staticmethod
    def _serialize_instance(instance: models.Model) -> dict[str, Any]:
        """Serialize a model instance to dictionary."""
        result: dict[str, Any] = {"_model": instance.__class__.__name__}
        meta = getattr(instance, "_meta", None)
        if not meta or not getattr(meta, "fields", None):
            # Allow lightweight objects in tests (and some service-layer calls).
            # We only capture simple, JSON-friendly attributes.
            for key, value in getattr(instance, "__dict__", {}).items():
                if key.startswith("_"):
                    continue
                if callable(value):
                    continue
                if value is None:
                    result[key] = None
                elif isinstance(value, datetime):
                    result[key] = value.isoformat()
                else:
                    result[key] = str(value) if not isinstance(value, (str, int, float, bool, list, dict)) else value
            # Include a stable identifier if present.
            if "pk" not in result and hasattr(instance, "pk"):
                result["pk"] = getattr(instance, "pk")
            return result

        for field in meta.fields:
            value = getattr(instance, field.name, None)
            if value is None:
                result[field.name] = None
            elif isinstance(value, datetime):
                result[field.name] = value.isoformat()
            elif isinstance(value, models.Model):
                result[field.name] = {"id": value.pk, "repr": str(value)[:100]}
            else:
                result[field.name] = str(value) if not isinstance(value, (str, int, float, bool)) else value
        return result

    @classmethod
    def _compute_changes(
        cls,
        old_instance: models.Model,
        new_instance: models.Model,
    ) -> list[FieldChange]:
        """Compute field-level changes between two model instances."""
        changes: list[FieldChange] = []
        model_name = new_instance.__class__.__name__
        ignored_fields = cls._ignored_fields.get(model_name, set())

        for field in new_instance._meta.fields:
            if field.name in ignored_fields:
                continue

            old_value = getattr(old_instance, field.name, None)
            new_value = getattr(new_instance, field.name, None)

            if old_value != new_value:
                changes.append(FieldChange(
                    field_name=field.name,
                    old_value=old_value,
                    new_value=new_value,
                    field_type=field.__class__.__name__,
                ))

        return changes


class AuditStorage(Protocol):
    """Protocol for audit storage backends."""

    def store(self, entry: AuditEntry) -> str:
        """Store an audit entry and return its ID."""
        ...

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
        """Query audit entries with filters."""
        ...


class InMemoryAuditStorage:
    """In-memory storage for testing and development."""

    def __init__(self, max_entries: int = 10000):
        self._entries: dict[str, AuditEntry] = {}
        self._max_entries = max_entries

    def store(self, entry: AuditEntry) -> str:
        """Store an audit entry."""
        if len(self._entries) >= self._max_entries:
            oldest_key = next(iter(self._entries))
            del self._entries[oldest_key]
        self._entries[entry.id] = entry
        return entry.id

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
        """Query audit entries with filters."""
        results: list[AuditEntry] = []

        for entry in sorted(self._entries.values(), key=lambda e: e.timestamp, reverse=True):
            if entity_type and entry.entity_type != entity_type:
                continue
            if entity_id is not None and entry.entity_id != entity_id:
                continue
            if action and entry.action != action:
                continue
            if user_id is not None and entry.context.user_id != user_id:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue

            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    def count(self) -> int:
        """Return total number of stored entries."""
        return len(self._entries)


class AuditMiddleware:
    """Django middleware for automatic audit context extraction.
    
    Attaches audit context to requests for use in signal handlers.
    """

    def __init__(self, get_response: Callable[[HttpRequest], Any]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> Any:
        """Process request and extract audit context."""
        request.audit_context = self._extract_context(request)
        response = self.get_response(request)
        return response

    def _extract_context(self, request: HttpRequest) -> AuditContext:
        """Extract audit context from request."""
        user = getattr(request, "user", None)
        request_id = getattr(request, "request_id", str(uuid.uuid4()))

        return AuditContext(
            user_id=user.pk if user and user.is_authenticated else None,
            user_email=user.email if user and user.is_authenticated else None,
            user_name=user.get_full_name() if user and user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
            request_id=request_id,
            session_id=request.session.session_key if hasattr(request, "session") else None,
        )

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str:
        """Extract client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


def get_current_context() -> AuditContext:
    """Get audit context from current thread/request.
    
    Returns empty context if not in request context.
    """
    from threading import local
    _thread_local = local()
    return getattr(_thread_local, "audit_context", AuditContext())


def set_current_context(context: AuditContext) -> None:
    """Set audit context for current thread."""
    from threading import local
    _thread_local = local()
    _thread_local.audit_context = context
