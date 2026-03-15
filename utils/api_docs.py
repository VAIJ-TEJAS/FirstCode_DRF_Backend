"""API Documentation configuration using drf-spectacular.

Provides OpenAPI/Swagger documentation for all API endpoints
with comprehensive schema customization.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.plumbing import build_array_type, build_basic_type
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_field,
    extend_schema_serializer,
    inline_serializer,
)
from rest_framework import serializers


class TokenAuthenticationScheme(OpenApiAuthenticationExtension):
    """OpenAPI authentication scheme for DRF Token Authentication."""

    target_class = "rest_framework.authentication.TokenAuthentication"
    name = "tokenAuth"

    def get_security_definition(self, auto_schema: AutoSchema) -> Dict[str, Any]:
        return {
            "type": "apiKey",
            "in": "header",
            "name": "Authorization",
            "description": "Token-based authentication. Format: Token <your_token>",
        }


def get_spectacular_settings() -> Dict[str, Any]:
    """Get drf-spectacular settings for the project.
    
    Returns a dictionary of settings for comprehensive API documentation.
    """
    return {
        "TITLE": "FirstCode API",
        "DESCRIPTION": """
# FirstCode Educational Platform API

This API provides comprehensive access to the FirstCode educational platform,
including course management, user progress tracking, live classes, and more.

## Authentication

All API endpoints require authentication using Token Authentication.
Include the header: `Authorization: Token <your_token>`

## Rate Limiting

API requests are rate-limited to ensure fair usage:
- Authenticated users: 1000 requests/hour
- Anonymous users: 100 requests/hour

## Pagination

List endpoints use cursor-based pagination with a default page size of 20
and a maximum of 100 items per page.

## Error Codes

- 400: Bad Request - Invalid input data
- 401: Unauthorized - Authentication required
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource does not exist
- 429: Too Many Requests - Rate limit exceeded
- 500: Internal Server Error
        """,
        "VERSION": "1.0.0",
        "SERVE_INCLUDE_SCHEMA": False,
        "COMPONENT_SPLIT_REQUEST": True,
        "SCHEMA_COERCE_PATH_PK_SUFFIX": True,
        "SCHEMA_COERCE_METHOD_NAMES": {
            "retrieve": "get",
            "list": "list",
            "create": "create",
            "update": "update",
            "partial_update": "partial_update",
            "destroy": "delete",
        },
        "EXCLUDE_TAGS": [],
        "EXTENSIONS": {
            "authentication": [TokenAuthenticationScheme],
        },
        "TAGS": [
            {"name": "Authentication", "description": "User authentication endpoints"},
            {"name": "Courses", "description": "Course management and retrieval"},
            {"name": "Chapters", "description": "Chapter management within courses"},
            {"name": "Lessons", "description": "Lesson content and progress"},
            {"name": "User Progress", "description": "Track user learning progress"},
            {"name": "Live Classes", "description": "Live class scheduling and attendance"},
            {"name": "Subscriptions", "description": "Subscription management"},
            {"name": "Orders", "description": "Order and payment processing"},
            {"name": "Audit Logs", "description": "Audit trail and activity monitoring"},
        ],
        "EXAMPLES_COMPONENT_SPLIT_REQUEST": True,
        "PREPROCESSING_HOOKS": [],
        "POSTPROCESSING_HOOKS": [
            "utils.api_docs.post_processing.remove_nullable_warnings",
        ],
    }


# Common response serializers for documentation
ErrorResponseSerializer = inline_serializer(
    name="ErrorResponse",
    fields={
        "error": serializers.CharField(help_text="Error message"),
        "code": serializers.CharField(help_text="Error code", required=False),
        "details": serializers.DictField(required=False),
    },
)

ValidationErrorSerializer = inline_serializer(
    name="ValidationErrorResponse",
    fields={
        "error": serializers.CharField(),
        "errors": serializers.DictField(
            child=serializers.ListField(child=serializers.CharField()),
            help_text="Field-specific validation errors",
        ),
    },
)

PaginatedResponseSerializer = inline_serializer(
    name="PaginatedResponse",
    fields={
        "count": serializers.IntegerField(help_text="Total number of items"),
        "next": serializers.URLField(help_text="URL to next page", allow_null=True),
        "previous": serializers.URLField(help_text="URL to previous page", allow_null=True),
        "results": serializers.ListField(help_text="List of results"),
    },
)


class CourseSchemaExtensions:
    """Schema extensions for Course endpoints."""

    LIST_PARAMETERS = [
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Search courses by name or description",
            examples=[
                OpenApiExample("Search Python", value="python"),
            ],
        ),
        OpenApiParameter(
            name="category",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter by category ID or slug",
        ),
        OpenApiParameter(
            name="is_paid",
            type=bool,
            location=OpenApiParameter.QUERY,
            description="Filter by paid/free courses",
        ),
        OpenApiParameter(
            name="main_category",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter by main category (Professional/Personal)",
            enum=["Professional", "Personal"],
        ),
    ]

    LIST_RESPONSE_EXAMPLE = OpenApiExample(
        "Course List Example",
        value={
            "count": 150,
            "next": "https://api.example.com/api/courses/?page=2",
            "previous": None,
            "results": [
                {
                    "id": 1,
                    "name": "Python Fundamentals",
                    "short_description": "Learn Python basics",
                    "category": {"id": 1, "name": "Programming"},
                    "is_paid": True,
                    "cover_image": "https://example.com/media/courses/python.jpg",
                    "created_at": "2024-01-15T10:30:00Z",
                }
            ],
        },
        response_only=True,
    )

    DETAIL_RESPONSE_EXAMPLE = OpenApiExample(
        "Course Detail Example",
        value={
            "id": 1,
            "name": "Python Fundamentals",
            "short_description": "Learn Python basics",
            "long_description": "Comprehensive Python course...",
            "requirements": "Basic computer knowledge",
            "category": {"id": 1, "name": "Programming"},
            "tags": [{"id": 1, "name": "Python"}, {"id": 2, "name": "Beginner"}],
            "tracks": [
                {
                    "id": 1,
                    "name": "Core Concepts",
                    "chapters": [
                        {
                            "id": 1,
                            "name": "Introduction",
                            "lessons_count": 5,
                        }
                    ],
                }
            ],
            "is_paid": True,
            "cover_image": "https://example.com/media/courses/python.jpg",
            "created_at": "2024-01-15T10:30:00Z",
        },
        response_only=True,
    )


class UserProgressSchemaExtensions:
    """Schema extensions for User Progress endpoints."""

    PROGRESS_RESPONSE_EXAMPLE = OpenApiExample(
        "User Progress Example",
        value={
            "course_id": 1,
            "course_name": "Python Fundamentals",
            "status": "In Progress",
            "progress": 45.5,
            "completed_chapters": 2,
            "total_chapters": 5,
            "started_at": "2024-02-01T08:00:00Z",
            "last_accessed_at": "2024-02-10T15:30:00Z",
            "certificate_id": None,
            "certificate_url": None,
        },
        response_only=True,
    )

    UPDATE_PROGRESS_REQUEST_EXAMPLE = OpenApiExample(
        "Update Progress Request",
        value={
            "lesson_id": 5,
            "completed": True,
            "time_spent_minutes": 30,
        },
        request_only=True,
    )


class AuditLogSchemaExtensions:
    """Schema extensions for Audit Log endpoints."""

    LIST_PARAMETERS = [
        OpenApiParameter(
            name="entity_type",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter by entity type (e.g., Course, User)",
            examples=[
                OpenApiExample("Filter by Course", value="Course"),
                OpenApiExample("Filter by User", value="User"),
            ],
        ),
        OpenApiParameter(
            name="entity_id",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter by entity ID",
        ),
        OpenApiParameter(
            name="action",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter by action type",
            enum=["create", "update", "delete", "view"],
        ),
        OpenApiParameter(
            name="user_id",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Filter by user ID",
        ),
        OpenApiParameter(
            name="start_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter entries after this date (ISO format)",
            examples=[
                OpenApiExample("Start of month", value="2024-02-01T00:00:00Z"),
            ],
        ),
        OpenApiParameter(
            name="end_date",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Filter entries before this date (ISO format)",
        ),
        OpenApiParameter(
            name="search",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Search in entity_repr, user_email, user_name",
        ),
        OpenApiParameter(
            name="page",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Page number",
            default=1,
        ),
        OpenApiParameter(
            name="limit",
            type=int,
            location=OpenApiParameter.QUERY,
            description="Items per page (max 100)",
            default=20,
        ),
        OpenApiParameter(
            name="sort",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Sort field",
            enum=["timestamp", "action", "entity_type", "user_email"],
            default="timestamp",
        ),
        OpenApiParameter(
            name="order",
            type=str,
            location=OpenApiParameter.QUERY,
            description="Sort order",
            enum=["asc", "desc"],
            default="desc",
        ),
    ]

    LIST_RESPONSE_EXAMPLE = OpenApiExample(
        "Audit Log List Example",
        value={
            "entries": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "timestamp": "2024-02-15T10:30:00Z",
                    "action": "update",
                    "level": "info",
                    "entity_type": "Course",
                    "entity_id": "123",
                    "entity_repr": "Python Fundamentals",
                    "context": {
                        "user_id": 42,
                        "user_email": "admin@example.com",
                        "user_name": "Admin User",
                        "ip_address": "192.168.1.1",
                    },
                    "changes": [
                        {
                            "field_name": "title",
                            "old_value": "Old Title",
                            "new_value": "New Title",
                        }
                    ],
                }
            ],
            "pagination": {
                "page": 1,
                "limit": 20,
                "total": 150,
                "pages": 8,
            },
        },
        response_only=True,
    )


class AuthenticationSchemaExtensions:
    """Schema extensions for Authentication endpoints."""

    LOGIN_REQUEST_EXAMPLE = OpenApiExample(
        "Login Request",
        value={
            "email": "user@example.com",
            "password": "securepassword123",
        },
        request_only=True,
    )

    LOGIN_RESPONSE_EXAMPLE = OpenApiExample(
        "Login Response",
        value={
            "token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b",
            "user_id": 42,
            "email": "user@example.com",
            "name": "John Doe",
        },
        response_only=True,
    )

    OTP_VERIFY_REQUEST_EXAMPLE = OpenApiExample(
        "OTP Verification Request",
        value={
            "email": "user@example.com",
            "otp": "123456",
        },
        request_only=True,
    )


# Post-processing hooks
def remove_nullable_warnings(result: dict, generator: Any, request: Any, public: bool) -> dict:
    """Post-processing hook to clean up schema warnings."""
    # Remove any nullable-related warnings that might be noisy
    if "components" in result and "schemas" in result["components"]:
        for schema_name, schema in result["components"]["schemas"].items():
            if "properties" in schema:
                for prop_name, prop in schema["properties"].items():
                    # Ensure consistent nullable handling
                    if "anyOf" in prop and len(prop["anyOf"]) == 2:
                        # Simplify anyOf with null to nullable pattern
                        non_null = [p for p in prop["anyOf"] if p.get("type") != "null"]
                        if len(non_null) == 1:
                            schema["properties"][prop_name] = {
                                **non_null[0],
                                "nullable": True,
                            }
    return result
