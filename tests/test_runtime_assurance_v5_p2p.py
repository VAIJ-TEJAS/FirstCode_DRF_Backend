from __future__ import annotations

from utils.runtime_assurance import build_runtime_report


def test_p2p_1621_runtime_report_marks_hardening_warnings() -> None:
    report = build_runtime_report({
        "APP_ENV": "production",
        "DJANGO_SECRET_KEY": "x",
        "DATABASE_URL": "postgres://db",
        "DEBUG": "false",
        "SESSION_COOKIE_SECURE": "false",
        "CSRF_COOKIE_SECURE": "false",
        "ALLOWED_HOSTS": "api.example.com",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
        "REDIS_URL": "redis://cache",
        "SENTRY_DSN": "https://dsn",
        "DEFAULT_FROM_EMAIL": "ops@example.com",
    })

    assert report["safe"] is True
    assert report["summary"]["warning"] >= 2


def test_p2p_1622_runtime_report_defaults_to_development() -> None:
    report = build_runtime_report({"DEBUG": "true"})
    assert report["environment"] == "development"
