from __future__ import annotations

from utils.runtime_assurance import build_runtime_report, normalize_environment


def test_p2p_1411_runtime_report_stable_for_stage_aliases() -> None:
    env = {
        "APP_ENV": "preprod",
        "DJANGO_SECRET_KEY": "x",
        "DATABASE_URL": "postgres://db",
        "DEBUG": "false",
        "SESSION_COOKIE_SECURE": "true",
        "CSRF_COOKIE_SECURE": "true",
        "ALLOWED_HOSTS": "stage.example.com",
        "CORS_ALLOWED_ORIGINS": "https://stage.example.com",
        "REDIS_URL": "redis://cache",
        "SENTRY_DSN": "https://dsn",
        "DEFAULT_FROM_EMAIL": "ops@example.com",
    }

    report = build_runtime_report(env)

    assert normalize_environment("preprod") == "staging"
    assert report["safe"] is True
    assert report["environment"] == "staging"


def test_p2p_1412_runtime_report_flags_missing_required_keys() -> None:
    report = build_runtime_report({"APP_ENV": "production", "DEBUG": "false"})
    assert report["safe"] is False
    assert report["summary"]["error"] >= 2
    assert report["score"] < 100
