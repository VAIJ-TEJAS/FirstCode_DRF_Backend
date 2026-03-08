"""Constants used by enterprise readiness modules."""

from __future__ import annotations

MANDATORY_ENV_VARS = [
    "DJANGO_SECRET_KEY",
    "DATABASE_URL",
]

RECOMMENDED_ENV_VARS = [
    "ALLOWED_HOSTS",
    "CORS_ALLOWED_ORIGINS",
    "SENTRY_DSN",
    "REDIS_URL",
    "EMAIL_HOST",
    "EMAIL_HOST_USER",
    "DEFAULT_FROM_EMAIL",
]

PRODUCTION_SAFETY_RULES = {
    "DEBUG": False,
    "SECURE_SSL_REDIRECT": True,
    "SESSION_COOKIE_SECURE": True,
    "CSRF_COOKIE_SECURE": True,
    "SECURE_CONTENT_TYPE_NOSNIFF": True,
    "SECURE_BROWSER_XSS_FILTER": True,
    "X_FRAME_OPTIONS": "DENY",
}

CACHE_RULES = {
    "cache_timeout_warning_seconds": 60,
    "cache_timeout_ok_seconds": 300,
}

READINESS_THRESHOLDS = {
    "database_query_ms_warn": 120,
    "database_query_ms_fail": 500,
    "disk_free_percent_warn": 15,
    "disk_free_percent_fail": 8,
    "clock_skew_ms_warn": 500,
    "clock_skew_ms_fail": 2500,
}

LIVE_CHECKS = ["service", "timestamp"]
READINESS_CHECKS = ["database", "cache", "disk", "clock", "config"]

STATUS_UP = "up"
STATUS_DEGRADED = "degraded"
STATUS_DOWN = "down"

DEFAULT_COMPONENT_STATUS = {
    "database": STATUS_UP,
    "cache": STATUS_UP,
    "disk": STATUS_UP,
    "clock": STATUS_UP,
    "config": STATUS_UP,
}
