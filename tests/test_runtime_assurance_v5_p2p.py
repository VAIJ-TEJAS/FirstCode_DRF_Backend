from __future__ import annotations

from utils.runtime_assurance import build_runtime_report, normalize_environment


def test_p2p_1511_runtime_report_flags_wildcard_hosts_in_prod() -> None:
    env = {
        "APP_ENV": "production",
        "DJANGO_SECRET_KEY": "x",
        "DATABASE_URL": "postgres://db",
        "DEBUG": "false",
        "SESSION_COOKIE_SECURE": "true",
        "CSRF_COOKIE_SECURE": "true",
        "ALLOWED_HOSTS": "*",
        "CORS_ALLOWED_ORIGINS": "https://app.example.com",
        "REDIS_URL": "redis://cache",
        "SENTRY_DSN": "https://dsn",
        "DEFAULT_FROM_EMAIL": "ops@example.com",
    }

    report = build_runtime_report(env)

    assert report["safe"] is False
    assert report["summary"]["error"] >= 1


def test_p2p_1512_normalize_environment_accepts_stage_alias() -> None:
    assert normalize_environment("stage") == "staging"
