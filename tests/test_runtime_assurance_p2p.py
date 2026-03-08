from __future__ import annotations

from utils.runtime_assurance import build_runtime_report, evaluate_runtime_environment, is_runtime_safe, summarize_issues


def test_p2p_001_production_safe_path_yields_safe_report() -> None:
    report = build_runtime_report(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "prod-secret",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SECURE": "true",
            "ALLOWED_HOSTS": "api.example.com",
            "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            "REDIS_URL": "redis://cache:6379/0",
            "SENTRY_DSN": "https://dsn.example.com",
            "DEFAULT_FROM_EMAIL": "noreply@example.com",
        }
    )

    assert report["safe"] is True
    assert report["score"] == 100


def test_p2p_002_staging_allows_warning_only_profiles() -> None:
    issues = evaluate_runtime_environment(
        {
            "APP_ENV": "staging",
            "DJANGO_SECRET_KEY": "stage-secret",
            "DATABASE_URL": "sqlite:///db",
            "DEBUG": "true",
            "ALLOWED_HOSTS": "*",
        }
    )

    assert is_runtime_safe(issues) is True


def test_p2p_003_summary_counts_errors_and_warnings() -> None:
    issues = evaluate_runtime_environment(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "",
            "DATABASE_URL": "",
            "DEBUG": "true",
            "ALLOWED_HOSTS": "*",
        }
    )

    summary = summarize_issues(issues)

    assert summary["error"] >= 3
    assert summary["warning"] >= 1


def test_p2p_004_safe_false_when_any_error_exists() -> None:
    issues = evaluate_runtime_environment(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "false",
        }
    )

    assert is_runtime_safe(issues) is False


def test_p2p_005_report_lines_and_issue_objects_stay_in_sync() -> None:
    report = build_runtime_report(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "false",
            "CSRF_COOKIE_SECURE": "false",
        }
    )

    assert len(report["lines"]) == len(report["issues"])


def test_p2p_006_score_is_lower_for_critical_profiles_than_warning_only_profiles() -> None:
    critical = build_runtime_report(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "",
            "DATABASE_URL": "",
            "DEBUG": "true",
            "ALLOWED_HOSTS": "*",
        }
    )

    warning_only = build_runtime_report(
        {
            "APP_ENV": "staging",
            "DJANGO_SECRET_KEY": "stage-secret",
            "DATABASE_URL": "sqlite:///db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "false",
            "CSRF_COOKIE_SECURE": "false",
        }
    )

    assert warning_only["score"] > critical["score"]


def test_p2p_007_summary_includes_info_bucket_even_when_unused() -> None:
    summary = summarize_issues([])
    assert "info" in summary


def test_p2p_008_runtime_report_environment_is_normalized() -> None:
    report = build_runtime_report(
        {
            "APP_ENV": "prod",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SECURE": "true",
            "ALLOWED_HOSTS": "api.example.com",
        }
    )

    assert report["environment"] == "production"
