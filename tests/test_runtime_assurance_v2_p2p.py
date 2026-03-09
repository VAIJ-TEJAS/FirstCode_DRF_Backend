from __future__ import annotations

from utils.runtime_assurance import build_runtime_report, evaluate_runtime_environment, readiness_score, summarize_issues


def test_p2p_1021_runtime_report_detects_prod_hardening_gaps() -> None:
    env = {
        "APP_ENV": "production",
        "DJANGO_SECRET_KEY": "x",
        "DATABASE_URL": "postgres://db",
        "DEBUG": "true",
        "SESSION_COOKIE_SECURE": "false",
        "CSRF_COOKIE_SECURE": "false",
        "ALLOWED_HOSTS": "*",
        "CORS_ALLOWED_ORIGINS": "https://example.com",
        "REDIS_URL": "redis://cache",
        "SENTRY_DSN": "https://dsn",
        "DEFAULT_FROM_EMAIL": "ops@example.com",
    }

    report = build_runtime_report(env)

    assert report["safe"] is False
    assert report["summary"]["error"] >= 2
    assert report["score"] < 100


def test_p2p_1022_runtime_summary_and_score_align_for_staging_env() -> None:
    env = {
        "APP_ENV": "staging",
        "DJANGO_SECRET_KEY": "x",
        "DATABASE_URL": "postgres://db",
        "DEBUG": "false",
        "SESSION_COOKIE_SECURE": "true",
        "CSRF_COOKIE_SECURE": "true",
        "ALLOWED_HOSTS": "staging.example.com",
        "CORS_ALLOWED_ORIGINS": "https://staging.example.com",
        "REDIS_URL": "redis://cache",
        "SENTRY_DSN": "https://dsn",
        "DEFAULT_FROM_EMAIL": "ops@example.com",
    }

    issues = evaluate_runtime_environment(env)
    summary = summarize_issues(issues)
    score = readiness_score(issues)

    assert summary["error"] == 0
    assert score == 100
