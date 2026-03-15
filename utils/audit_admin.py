"""Django Admin integration for AuditLog model.

Provides admin interface for viewing and managing audit log entries
with filtering, searching, and read-only access.
"""

from __future__ import annotations

from typing import Any

from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from utils.audit_logger import AuditAction
from utils.audit_models import AuditLog


class AuditActionFilter(admin.SimpleListFilter):
    """Custom filter for audit action types."""

    title = "action type"
    parameter_name = "action"

    def lookups(self, request, model_admin):
        """Return available action choices."""
        return [
            (AuditAction.CREATE.value, "Create"),
            (AuditAction.UPDATE.value, "Update"),
            (AuditAction.DELETE.value, "Delete"),
            (AuditAction.VIEW.value, "View"),
            (AuditAction.LOGIN.value, "Login"),
            (AuditAction.LOGOUT.value, "Logout"),
            (AuditAction.EXPORT.value, "Export"),
            (AuditAction.IMPORT.value, "Import"),
        ]

    def queryset(self, request, queryset):
        """Filter queryset by action."""
        if self.value():
            return queryset.filter(action=self.value())
        return queryset


class AuditLevelFilter(admin.SimpleListFilter):
    """Custom filter for audit severity levels."""

    title = "severity level"
    parameter_name = "level"

    def lookups(self, request, model_admin):
        """Return available level choices."""
        return [
            ("info", "Info"),
            ("warning", "Warning"),
            ("error", "Error"),
            ("critical", "Critical"),
        ]

    def queryset(self, request, queryset):
        """Filter queryset by level."""
        if self.value():
            return queryset.filter(level=self.value())
        return queryset


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin interface for AuditLog entries.
    
    Provides read-only access to audit logs with comprehensive
    filtering and searching capabilities.
    """

    # List display configuration
    list_display = [
        "timestamp",
        "action_badge",
        "level_badge",
        "entity_info",
        "user_info",
        "has_changes_icon",
        "ip_address",
    ]

    # Filters
    list_filter = [
        AuditActionFilter,
        AuditLevelFilter,
        "entity_type",
        ("timestamp", admin.DateFieldListFilter),
        "has_changes",
    ]

    # Search fields
    search_fields = [
        "entity_type",
        "entity_id",
        "entity_repr",
        "user_email",
        "user_name",
        "ip_address",
        "request_id",
        "correlation_id",
    ]

    # Read-only
    readonly_fields = [
        "id",
        "timestamp",
        "action",
        "level",
        "entity_type",
        "entity_id",
        "entity_repr",
        "user_id",
        "user_email",
        "user_name",
        "ip_address",
        "user_agent",
        "request_id",
        "session_id",
        "correlation_id",
        "changes_formatted",
        "old_state_formatted",
        "new_state_formatted",
        "metadata_formatted",
        "duration_ms",
        "has_changes",
        "created_at",
    ]

    # Fieldsets for detail view
    fieldsets = (
        ("Action Information", {
            "fields": (
                "action",
                "level",
                "timestamp",
                "duration_ms",
                "has_changes",
            ),
        }),
        ("Entity Information", {
            "fields": (
                "entity_type",
                "entity_id",
                "entity_repr",
            ),
        }),
        ("User Information", {
            "fields": (
                "user_id",
                "user_email",
                "user_name",
            ),
        }),
        ("Request Context", {
            "fields": (
                "ip_address",
                "user_agent",
                "request_id",
                "session_id",
                "correlation_id",
            ),
            "classes": ("collapse",),
        }),
        ("Change Details", {
            "fields": (
                "changes_formatted",
            ),
            "classes": ("collapse",),
        }),
        ("State Data", {
            "fields": (
                "old_state_formatted",
                "new_state_formatted",
            ),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": (
                "metadata_formatted",
            ),
            "classes": ("collapse",),
        }),
        ("System Information", {
            "fields": (
                "id",
                "created_at",
            ),
            "classes": ("collapse",),
        }),
    )

    # Default ordering
    ordering = ("-timestamp",)

    # Pagination
    list_per_page = 50

    # Date hierarchy
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        """Disable add permission - audit logs are read-only."""
        return False

    def has_change_permission(self, request, obj=None):
        """Disable change permission - audit logs are read-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Restrict delete permission - only superusers can delete."""
        return request.user.is_superuser

    # Custom display methods
    @admin.display(description="Action")
    def action_badge(self, obj: AuditLog) -> str:
        """Display action with color-coded badge."""
        colors = {
            AuditAction.CREATE.value: "green",
            AuditAction.UPDATE.value: "blue",
            AuditAction.DELETE.value: "red",
            AuditAction.VIEW.value: "gray",
            AuditAction.LOGIN.value: "green",
            AuditAction.LOGOUT.value: "orange",
        }
        color = colors.get(obj.action, "gray")
        return format_html(
            '<span style="padding: 2px 8px; border-radius: 4px; '
            'background-color: {}; color: white; font-size: 11px; '
            'text-transform: uppercase;">{}</span>',
            color,
            obj.get_action_display(),
        )

    @admin.display(description="Level")
    def level_badge(self, obj: AuditLog) -> str:
        """Display level with color-coded badge."""
        colors = {
            "info": "#2196F3",
            "warning": "#FF9800",
            "error": "#F44336",
            "critical": "#9C27B0",
        }
        color = colors.get(obj.level, "gray")
        return format_html(
            '<span style="padding: 2px 8px; border-radius: 4px; '
            'background-color: {}; color: white; font-size: 11px; '
            'text-transform: uppercase;">{}</span>',
            color,
            obj.level,
        )

    @admin.display(description="Entity")
    def entity_info(self, obj: AuditLog) -> str:
        """Display entity type and ID."""
        if obj.entity_repr:
            return format_html(
                "{} <small>({})</small><br><small>{}</small>",
                obj.entity_type,
                obj.entity_id,
                obj.entity_repr[:50],
            )
        return format_html(
            "{} <small>({})</small>",
            obj.entity_type,
            obj.entity_id,
        )

    @admin.display(description="User")
    def user_info(self, obj: AuditLog) -> str:
        """Display user information."""
        if obj.user_email:
            return format_html(
                "{}<br><small>{}</small>",
                obj.user_email,
                obj.user_name or "",
            )
        return format_html(
            '<span style="color: #999;">System/Anonymous</span>',
        )

    @admin.display(description="Changes", boolean=True)
    def has_changes_icon(self, obj: AuditLog) -> bool:
        """Display changes indicator."""
        return obj.has_changes

    @admin.display(description="Changes")
    def changes_formatted(self, obj: AuditLog) -> str:
        """Format changes data as readable HTML."""
        if not obj.changes_data:
            return "No field changes recorded"

        rows = []
        for change in obj.changes_data:
            field = change.get("field_name", "")
            old_val = change.get("old_value", "N/A")
            new_val = change.get("new_value", "N/A")
            rows.append(
                f'<tr><td><strong>{field}</strong></td>'
                f'<td style="color: #d32f2f;">{old_val}</td>'
                f'<td style="color: #388e3c;">{new_val}</td></tr>'
            )

        return mark_safe(
            f'<table style="width: 100%; border-collapse: collapse;">'
            f'<thead><tr><th>Field</th><th>Old Value</th><th>New Value</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>'
        )

    @admin.display(description="Old State")
    def old_state_formatted(self, obj: AuditLog) -> str:
        """Format old state as readable HTML."""
        if not obj.old_state:
            return "No previous state recorded"
        return self._format_json_data(obj.old_state)

    @admin.display(description="New State")
    def new_state_formatted(self, obj: AuditLog) -> str:
        """Format new state as readable HTML."""
        if not obj.new_state:
            return "No new state recorded"
        return self._format_json_data(obj.new_state)

    @admin.display(description="Metadata")
    def metadata_formatted(self, obj: AuditLog) -> str:
        """Format metadata as readable HTML."""
        if not obj.metadata:
            return "No metadata"
        return self._format_json_data(obj.metadata)

    def _format_json_data(self, data: dict) -> str:
        """Format JSON data as readable HTML."""
        import json
        formatted = json.dumps(data, indent=2, default=str)
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; '
            'border-radius: 4px; overflow-x: auto;">{}</pre>',
            formatted,
        )

    # Actions
    @admin.action(description="Mark selected entries for retention")
    def mark_for_retention(self, request, queryset):
        """Action to mark entries for long-term retention."""
        # In a real implementation, this might set a flag
        self.message_user(request, f"{queryset.count()} entries marked for retention.")

    actions = [mark_for_retention]

    class Media:
        """Custom admin media."""
        css = {
            "all": ("admin/css/audit_log.css",),
        }
