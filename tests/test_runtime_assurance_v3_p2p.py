from __future__ import annotations

from utils.runtime_assurance import build_runtime_report, evaluate_runtime_environment, readiness_score


def test_p2p_1311_runtime_report_consistency_for_hardened_production() -> None:
    env = {
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

    report = build_runtime_report(env)

    assert report["safe"] is True
    assert report["summary"]["error"] == 0
    assert report["score"] == 100


def test_p2p_1312_runtime_issue_score_degrades_with_missing_keys() -> None:
    env = {
        "APP_ENV": "production",
        "DEBUG": "false",
    }

    issues = evaluate_runtime_environment(env)
    score = readiness_score(issues)

    assert len(issues) > 0
    assert score < 100
