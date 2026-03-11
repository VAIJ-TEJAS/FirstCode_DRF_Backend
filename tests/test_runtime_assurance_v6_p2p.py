from __future__ import annotations

from utils.runtime_assurance import build_runtime_report


def test_p2p_1611_runtime_report_flags_missing_required_keys() -> None:
    report = build_runtime_report({"APP_ENV": "production", "DEBUG": "false"})
    assert report["safe"] is False
    assert report["summary"]["error"] >= 2


def test_p2p_1612_runtime_report_ok_for_hardened_env() -> None:
    report = build_runtime_report(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "x",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SECURE": "true",
            "ALLOWED_HOSTS": "api.example.com",
            "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            "REDIS_URL": "redis://cache",
            "SENTRY_DSN": "https://dsn",
            "DEFAULT_FROM_EMAIL": "ops@example.com",
        }
    )

    assert report["safe"] is True
