"""REST API endpoints for audit log queries.

Provides API endpoints for querying and retrieving audit log entries
with filtering, pagination, and aggregation capabilities.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Q
from django.utils import timezone as django_tz

from utils.audit_logger import AuditAction, AuditEntry, AuditLogger
from utils.audit_models import AuditLog, DjangoAuditStorage


class AuditLogQueryParams:
    """Helper class for parsing and validating query parameters."""

    def __init__(self, request: Request):
        self.request = request
        self.errors: list[str] = []

    def get_entity_type(self) -> Optional[str]:
        """Get entity type filter."""
        return self.request.query_params.get("entity_type")

    def get_entity_id(self) -> Optional[str]:
        """Get entity ID filter."""
        return self.request.query_params.get("entity_id")

    def get_action(self) -> Optional[str]:
        """Get action filter and validate."""
        action = self.request.query_params.get("action")
        if action and action not in [a.value for a in AuditAction]:
            self.errors.append(f"Invalid action: {action}")
            return None
        return action

    def get_user_id(self) -> Optional[int]:
        """Get user ID filter."""
        user_id = self.request.query_params.get("user_id")
        if user_id:
            try:
                return int(user_id)
            except ValueError:
                self.errors.append(f"Invalid user_id: {user_id}")
        return None

    def get_date_range(self) -> tuple[Optional[datetime], Optional[datetime]]:
        """Get start and end date filters."""
        start_str = self.request.query_params.get("start_date")
        end_str = self.request.query_params.get("end_date")

        start_date = None
        end_date = None

        if start_str:
            try:
                start_date = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
            except ValueError:
                self.errors.append(f"Invalid start_date format: {start_str}")

        if end_str:
            try:
                end_date = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except ValueError:
                self.errors.append(f"Invalid end_date format: {end_str}")

        return start_date, end_date

    def get_pagination(self) -> tuple[int, int]:
        """Get page and limit parameters."""
        try:
            page = max(1, int(self.request.query_params.get("page", 1)))
        except ValueError:
            page = 1

        try:
            limit = max(1, min(100, int(self.request.query_params.get("limit", 20))))
        except ValueError:
            limit = 20

        return page, limit

    def get_search(self) -> Optional[str]:
        """Get search query."""
        return self.request.query_params.get("search")

    def get_sort(self) -> tuple[str, str]:
        """Get sort field and order."""
        sort_field = self.request.query_params.get("sort", "timestamp")
        sort_order = self.request.query_params.get("order", "desc")

        # Validate sort field
        valid_fields = {
            "timestamp", "action", "level", "entity_type", "entity_id",
            "user_email", "created_at",
        }
        if sort_field not in valid_fields:
            sort_field = "timestamp"

        # Validate sort order
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        return sort_field, sort_order


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def audit_log_list(request: Request) -> Response:
    """List audit log entries with filtering and pagination.
    
    Query Parameters:
        entity_type: Filter by entity type (e.g., "Course", "User")
        entity_id: Filter by entity ID
        action: Filter by action type (create, update, delete, view)
        user_id: Filter by user ID who performed the action
        start_date: Filter entries after this date (ISO format)
        end_date: Filter entries before this date (ISO format)
        search: Search in entity_repr, user_email, user_name
        page: Page number (default: 1)
        limit: Items per page (default: 20, max: 100)
        sort: Sort field (default: timestamp)
        order: Sort order (asc/desc, default: desc)
        
    Returns:
        Paginated list of audit log entries with metadata
        
    Example:
        GET /api/audit/logs/?entity_type=Course&action=update&limit=50
    """
    params = AuditLogQueryParams(request)

    # Build queryset
    queryset = AuditLog.objects.all()

    # Apply filters
    if entity_type := params.get_entity_type():
        queryset = queryset.filter(entity_type=entity_type)

    if entity_id := params.get_entity_id():
        queryset = queryset.filter(entity_id=entity_id)

    if action := params.get_action():
        queryset = queryset.filter(action=action)

    if user_id := params.get_user_id():
        queryset = queryset.filter(user_id=user_id)

    start_date, end_date = params.get_date_range()
    if start_date:
        queryset = queryset.filter(timestamp__gte=start_date)
    if end_date:
        queryset = queryset.filter(timestamp__lte=end_date)

    if search := params.get_search():
        queryset = queryset.filter(
            Q(entity_repr__icontains=search) |
            Q(user_email__icontains=search) |
            Q(user_name__icontains=search) |
            Q(entity_type__icontains=search)
        )

    # Apply sorting
    sort_field, sort_order = params.get_sort()
    sort_prefix = "-" if sort_order == "desc" else ""
    queryset = queryset.order_by(f"{sort_prefix}{sort_field}")

    # Apply pagination
    page, limit = params.get_pagination()
    total = queryset.count()
    offset = (page - 1) * limit
    entries = queryset[offset:offset + limit]

    # Return response
    return Response({
        "entries": [entry.to_audit_entry().to_dict() for entry in entries],
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
        },
        "filters": {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "action": action,
            "user_id": user_id,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "search": search,
        },
        "sort": {
            "field": sort_field,
            "order": sort_order,
        },
        "errors": params.errors if params.errors else None,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def audit_log_detail(request: Request, log_id: str) -> Response:
    """Get detailed information about a single audit log entry.
    
    Args:
        log_id: UUID of the audit log entry
        
    Returns:
        Full audit log entry details including all state data
        
    Example:
        GET /api/audit/logs/123e4567-e89b-12d3-a456-426614174000/
    """
    try:
        log = AuditLog.objects.get(id=log_id)
    except AuditLog.DoesNotExist:
        return Response(
            {"error": "Audit log entry not found"},
            status=status.HTTP_404_NOT_FOUND,
        )

    return Response(log.to_audit_entry().to_dict())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def audit_entity_history(request: Request, entity_type: str, entity_id: str) -> Response:
    """Get audit history for a specific entity.
    
    Args:
        entity_type: Type of entity (e.g., "Course", "Chapter")
        entity_id: ID of the entity
        
    Query Parameters:
        limit: Maximum entries to return (default: 50, max: 200)
        
    Returns:
        Chronological history of changes for the entity
        
    Example:
        GET /api/audit/history/Course/123/
    """
    try:
        limit = min(200, max(1, int(request.query_params.get("limit", 50))))
    except ValueError:
        limit = 50

    entries = AuditLog.objects.get_entity_history(entity_type, entity_id, limit=limit)

    return Response({
        "entity_type": entity_type,
        "entity_id": entity_id,
        "total_entries": AuditLog.objects.filter(
            entity_type=entity_type,
            entity_id=entity_id,
        ).count(),
        "entries": [entry.to_audit_entry().to_dict() for entry in entries],
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def audit_user_activity(request: Request, user_id: int) -> Response:
    """Get audit activity for a specific user.
    
    Args:
        user_id: ID of the user to query
        
    Query Parameters:
        days: Number of days to look back (default: 30)
        limit: Maximum entries to return (default: 100)
        
    Returns:
        User's activity history
        
    Example:
        GET /api/audit/users/42/activity/?days=7
    """
    try:
        days = min(365, max(1, int(request.query_params.get("days", 30))))
        limit = min(200, max(1, int(request.query_params.get("limit", 100))))
    except ValueError:
        days = 30
        limit = 100

    start_time = django_tz.now() - timedelta(days=days)
    entries = AuditLog.objects.get_user_activity(user_id, start_time=start_time, limit=limit)

    # Get action summary
    action_summary = (
        AuditLog.objects.filter(user_id=user_id, timestamp__gte=start_time)
        .values("action")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    return Response({
        "user_id": user_id,
        "period_days": days,
        "total_entries": len(entries),
        "action_summary": {item["action"]: item["count"] for item in action_summary},
        "entries": [entry.to_audit_entry().to_dict() for entry in entries],
    })


@api_view(["GET"])
@permission_classes([IsAdminUser])
def audit_statistics(request: Request) -> Response:
    """Get audit log statistics (admin only).
    
    Query Parameters:
        days: Statistics period in days (default: 30, max: 365)
        
    Returns:
        Aggregated statistics about audit log activity
        
    Example:
        GET /api/audit/statistics/?days=30
    """
    try:
        days = min(365, max(1, int(request.query_params.get("days", 30))))
    except ValueError:
        days = 30

    storage = DjangoAuditStorage()
    stats = storage.get_stats(days=days)

    # Get top entity types
    cutoff = django_tz.now() - timedelta(days=days)
    top_entities = list(
        AuditLog.objects.filter(timestamp__gte=cutoff)
        .values("entity_type")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Get top users by activity
    top_users = list(
        AuditLog.objects.filter(timestamp__gte=cutoff, user_id__isnull=False)
        .values("user_id", "user_email", "user_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )

    # Hourly distribution
    hourly_distribution = list(
        AuditLog.objects.filter(timestamp__gte=cutoff)
        .extra({"hour": "EXTRACT(hour FROM timestamp)"})
        .values("hour")
        .annotate(count=Count("id"))
        .order_by("hour")
    )

    return Response({
        "period_days": days,
        "total_entries": stats["total_entries"],
        "by_action": stats["by_action"],
        "by_level": stats["by_level"],
        "by_entity_type": stats["by_entity_type"],
        "unique_users": stats["unique_users"],
        "date_range": stats["date_range"],
        "top_entity_types": top_entities,
        "top_users": top_users,
        "hourly_distribution": hourly_distribution,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def audit_manual_log(request: Request) -> Response:
    """Manually create an audit log entry.
    
    Request Body:
        action: Action type (required)
        entity_type: Entity type (required)
        entity_id: Entity ID (optional)
        metadata: Additional metadata dict (optional)
        changes: List of field changes (optional)
        
    Returns:
        Created audit log entry ID
        
    Example:
        POST /api/audit/log/
        {
            "action": "export",
            "entity_type": "Course",
            "entity_id": "123",
            "metadata": {"format": "csv", "record_count": 50}
        }
    """
    from utils.audit_signals import manual_audit_log

    action = request.data.get("action")
    entity_type = request.data.get("entity_type")
    entity_id = request.data.get("entity_id")
    metadata = request.data.get("metadata", {})
    changes = request.data.get("changes")

    if not action or not entity_type:
        return Response(
            {"error": "action and entity_type are required"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    entry_id = manual_audit_log(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        user=request.user,
        metadata=metadata,
        changes=changes,
    )

    if entry_id:
        return Response({
            "id": entry_id,
            "message": "Audit log entry created successfully",
        })
    else:
        return Response(
            {"error": "Audit logging is disabled"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
