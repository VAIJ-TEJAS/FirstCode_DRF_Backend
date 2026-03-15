"""Django App configuration for audit logging.

This module provides the Django app configuration and initialization
for the audit logging system.
"""

from __future__ import annotations

import logging
from typing import Any

from django.apps import AppConfig
from django.conf import settings
from django.core.checks import CheckMessage, run_checks
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)


class AuditLogConfig(AppConfig):
    """Configuration for the audit logging system.
    
    This app provides comprehensive audit logging capabilities including:
    - Automatic change tracking via middleware
    - Manual audit logging API
    - Audit log querying and filtering
    - Data diff generation for updates
    """

    name = "utils.audit"
    label = "audit"
    verbose_name = "Audit Logging"

    def ready(self) -> None:
        """Initialize the audit logging system when Django starts.
        
        This method is called when the app registry is fully populated.
        """
        # Import signal handlers to register them
        try:
            from utils.audit_signals import enable_audit_logging

            # Auto-enable if configured in settings
            audit_settings = getattr(settings, "AUDIT_LOG", {})
            if audit_settings.get("AUTO_ENABLE", True):
                enable_audit_logging()
                logger.info("Audit logging system auto-enabled")

            # Import admin configuration
            from utils import audit_admin  # noqa: F401

        except ImportError as e:
            logger.warning(f"Could not initialize audit logging: {e}")


def check_audit_configuration(**kwargs: Any) -> list[CheckMessage]:
    """Django system check for audit configuration.
    
    Checks that the audit logging system is properly configured.
    """
    errors: list[CheckMessage] = []

    # Check for audit log model in database
    try:
        from utils.audit_models import AuditLog
        # Try to access the model to verify it's available
        AuditLog._meta.get_fields()
    except Exception as e:
        errors.append(
            CheckMessage(
                "AuditLog model not available",
                hint="Run migrations to create the AuditLog table",
                obj="audit.AuditLog",
                id="audit.E001",
            )
        )

    return errors


# Default app configuration
default_app_config = "utils.audit.AuditLogConfig"
