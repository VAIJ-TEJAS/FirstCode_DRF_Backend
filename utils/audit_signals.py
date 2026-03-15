"""Django signal handlers for automatic audit logging.

Connects to Django's post_save and post_delete signals to automatically
create audit log entries for model changes.
"""

from __future__ import annotations

import threading
from typing import Any, Optional, Type

from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from utils.audit_logger import AuditContext, AuditLogger
from utils.audit_models import AuditLog, DjangoAuditStorage

# Thread-local storage for tracking model state during save operations
_thread_local = threading.local()

# Models that should not be audited (to avoid recursive logging)
AUDIT_EXCLUDED_MODELS = {
    "AuditLog",
    "LogEntry",  # Django admin logs
    "Session",
    "Migration",
    "ContentType",
}

# Fields that should be ignored in change tracking (common auto-updated fields)
DEFAULT_IGNORED_FIELDS = {
    "id",
    "created_at",
    "updated_at",
    "last_modified",
    "modified_at",
    "created",
    "modified",
}


def get_audit_context_from_request() -> AuditContext:
    """Extract audit context from current request in thread."""
    request = getattr(_thread_local, "request", None)
    if request is None:
        return AuditContext()

    user = getattr(request, "user", None)
    return AuditContext(
        user_id=user.pk if user and hasattr(user, "is_authenticated") and user.is_authenticated else None,
        user_email=user.email if user and hasattr(user, "is_authenticated") and user.is_authenticated else None,
        user_name=user.get_full_name() if user and hasattr(user, "get_full_name") and user.is_authenticated else None,
        ip_address=getattr(request, "META", {}).get("HTTP_X_FORWARDED_FOR", "") or 
                   getattr(request, "META", {}).get("REMOTE_ADDR", ""),
        user_agent=getattr(request, "META", {}).get("HTTP_USER_AGENT", ""),
        request_id=getattr(request, "request_id", None),
        session_id=getattr(request, "session", {}).get("session_key", None) if hasattr(request, "session") else None,
    )


def should_audit_model(model_class: Type[models.Model]) -> bool:
    """Check if a model should be audited."""
    model_name = model_class.__name__

    # Skip explicitly excluded models
    if model_name in AUDIT_EXCLUDED_MODELS:
        return False

    # Skip abstract models
    if model_class._meta.abstract:
        return False

    # Skip proxy models (audit the concrete model instead)
    if model_class._meta.proxy:
        return False

    # Check for explicit opt-out via model attribute
    if hasattr(model_class, "_audit_excluded") and model_class._audit_excluded:
        return False

    return True


def get_old_instance_state(instance: models.Model) -> Optional[models.Model]:
    """Retrieve the old state of an instance before save."""
    if instance.pk is None:
        return None

    # Try to fetch the current state from database
    try:
        return instance.__class__.objects.get(pk=instance.pk)
    except instance.__class__.DoesNotExist:
        return None


def store_pre_save_state(instance: models.Model) -> None:
    """Store the pre-save state of an instance for later comparison."""
    if not hasattr(_thread_local, "pre_save_states"):
        _thread_local.pre_save_states = {}

    key = f"{instance.__class__.__name__}:{instance.pk}"

    # Only store if we haven't already (first pre_save signal)
    if key not in _thread_local.pre_save_states:
        old_instance = get_old_instance_state(instance)
        if old_instance:
            _thread_local.pre_save_states[key] = old_instance


def get_pre_save_state(instance: models.Model) -> Optional[models.Model]:
    """Retrieve the stored pre-save state."""
    key = f"{instance.__class__.__name__}:{instance.pk}"
    state = getattr(_thread_local, "pre_save_states", {}).get(key)

    # Clean up
    if hasattr(_thread_local, "pre_save_states"):
        _thread_local.pre_save_states.pop(key, None)

    return state


@receiver(pre_save)
def audit_pre_save_handler(
    sender: Type[models.Model],
    instance: models.Model,
    **kwargs: Any,
) -> None:
    """Capture state before save for change tracking."""
    if not should_audit_model(sender):
        return

    if not AuditLogger.is_enabled():
        return

    # Store the pre-save state
    store_pre_save_state(instance)


@receiver(post_save)
def audit_post_save_handler(
    sender: Type[models.Model],
    instance: models.Model,
    created: bool,
    **kwargs: Any,
) -> None:
    """Create audit log entry after model save."""
    if not should_audit_model(sender):
        return

    if not AuditLogger.is_enabled():
        return

    context = get_audit_context_from_request()

    if created:
        # Log create operation
        AuditLogger.log_create(
            instance=instance,
            context=context,
            metadata={
                "signal": "post_save",
                "raw": kwargs.get("raw", False),
                "using": kwargs.get("using", "default"),
            },
        )
    else:
        # Log update operation
        old_instance = get_pre_save_state(instance)
        if old_instance:
            AuditLogger.log_update(
                old_instance=old_instance,
                new_instance=instance,
                context=context,
                metadata={
                    "signal": "post_save",
                    "raw": kwargs.get("raw", False),
                    "using": kwargs.get("using", "default"),
                },
            )


@receiver(post_delete)
def audit_post_delete_handler(
    sender: Type[models.Model],
    instance: models.Model,
    **kwargs: Any,
) -> None:
    """Create audit log entry after model deletion."""
    if not should_audit_model(sender):
        return

    if not AuditLogger.is_enabled():
        return

    context = get_audit_context_from_request()

    AuditLogger.log_delete(
        instance=instance,
        context=context,
        metadata={
            "signal": "post_delete",
            "using": kwargs.get("using", "default"),
        },
    )


class AuditSignalMiddleware:
    """Middleware to store request context for signal handlers.
    
    This middleware stores the current request in thread-local storage
    so that signal handlers can access user and request information.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """Store request and process response."""
        # Store request in thread-local
        _thread_local.request = request

        # Initialize pre_save state storage
        if not hasattr(_thread_local, "pre_save_states"):
            _thread_local.pre_save_states = {}

        response = self.get_response(request)

        # Clean up thread-local
        _thread_local.request = None
        _thread_local.pre_save_states = {}

        return response


def enable_audit_logging() -> None:
    """Enable audit logging with Django storage backend.
    
    Call this in your Django app's ready() method.
    """
    storage = DjangoAuditStorage()
    AuditLogger.configure(storage=storage, enabled=True)


def disable_audit_logging() -> None:
    """Temporarily disable audit logging."""
    AuditLogger.configure(enabled=False)


def is_audit_enabled() -> bool:
    """Check if audit logging is currently enabled."""
    return AuditLogger.is_enabled()


# Decorator for temporarily disabling audit in a code block
class audit_disabled:
    """Context manager to temporarily disable audit logging.
    
    Usage:
        with audit_disabled():
            # Operations here will not be audited
            bulk_create_models()
    """

    def __enter__(self):
        self._was_enabled = AuditLogger.is_enabled()
        disable_audit_logging()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._was_enabled:
            storage = DjangoAuditStorage()
            AuditLogger.configure(storage=storage, enabled=True)
        return False


def manual_audit_log(
    action: str,
    entity_type: str,
    entity_id: Optional[Any] = None,
    user: Optional[Any] = None,
    metadata: Optional[dict] = None,
    changes: Optional[list] = None,
) -> Optional[str]:
    """Manually create an audit log entry.
    
    This function allows creating audit log entries for operations
    that aren't automatically captured by signals.
    
    Args:
        action: The action type (create, update, delete, view, etc.)
        entity_type: Type of entity affected
        entity_id: Entity identifier
        user: User object or dict with user info
        metadata: Additional metadata dict
        changes: List of change dicts with field_name, old_value, new_value
        
    Returns:
        Entry ID if logged successfully
        
    Example:
        manual_audit_log(
            action="export",
            entity_type="Course",
            entity_id=123,
            user=request.user,
            metadata={"format": "csv", "record_count": 50}
        )
    """
    from utils.audit_logger import AuditAction, AuditLevel, AuditEntry, FieldChange

    if not AuditLogger.is_enabled():
        return None

    # Build context from user
    context = AuditContext()
    if user:
        if hasattr(user, "pk"):
            context = AuditContext(
                user_id=user.pk,
                user_email=getattr(user, "email", None),
                user_name=user.get_full_name() if hasattr(user, "get_full_name") else str(user),
            )
        elif isinstance(user, dict):
            context = AuditContext(
                user_id=user.get("id"),
                user_email=user.get("email"),
                user_name=user.get("name"),
            )

    # Build field changes
    field_changes = []
    if changes:
        field_changes = [
            FieldChange(
                field_name=c.get("field_name", ""),
                old_value=c.get("old_value"),
                new_value=c.get("new_value"),
                field_type=c.get("field_type", ""),
            )
            for c in changes
        ]

    entry = AuditEntry(
        action=AuditAction(action) if action in [a.value for a in AuditAction] else AuditAction.VIEW,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        context=context,
        changes=field_changes,
        metadata=metadata or {},
    )

    return AuditLogger.log(entry)
