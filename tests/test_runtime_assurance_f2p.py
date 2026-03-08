from __future__ import annotations

from utils.runtime_assurance import (
    build_runtime_report,
    evaluate_runtime_environment,
    format_issue_lines,
    normalize_environment,
    readiness_score,
)


def test_f2p_001_environment_aliases_are_normalized_consistently() -> None:
    assert normalize_environment("prod") == "production"
    assert normalize_environment("stage") == "staging"
    assert normalize_environment("dev") == "development"


def test_f2p_002_missing_required_keys_generate_errors() -> None:
    issues = evaluate_runtime_environment({"APP_ENV": "production"})

    assert any(issue.key == "DJANGO_SECRET_KEY" and issue.severity == "error" for issue in issues)
    assert any(issue.key == "DATABASE_URL" and issue.severity == "error" for issue in issues)


def test_f2p_003_recommended_keys_generate_warning_not_error() -> None:
    issues = evaluate_runtime_environment(
        {
            "APP_ENV": "staging",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "sqlite:///db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SECURE": "true",
        }
    )

    assert any(issue.key == "REDIS_URL" and issue.severity == "warning" for issue in issues)


def test_f2p_004_production_debug_true_is_blocking() -> None:
    issues = evaluate_runtime_environment(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "true",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SECURE": "true",
            "ALLOWED_HOSTS": "api.example.com",
        }
    )

    assert any(issue.key == "DEBUG" and issue.severity == "error" for issue in issues)


def test_f2p_005_wildcard_hosts_are_rejected_in_production() -> None:
    issues = evaluate_runtime_environment(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SECURE": "true",
            "ALLOWED_HOSTS": "*",
        }
    )

    assert any(issue.key == "ALLOWED_HOSTS" and issue.severity == "error" for issue in issues)


def test_f2p_006_readiness_score_decreases_with_more_issues() -> None:
    clean = readiness_score([])

    noisy = readiness_score(
        evaluate_runtime_environment(
            {
                "APP_ENV": "production",
                "DJANGO_SECRET_KEY": "",
                "DATABASE_URL": "",
                "DEBUG": "true",
                "ALLOWED_HOSTS": "*",
            }
        )
    )

    assert clean == 100
    assert noisy < clean


def test_f2p_007_issue_lines_are_human_readable() -> None:
    issues = evaluate_runtime_environment(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "",
            "DATABASE_URL": "",
            "DEBUG": "true",
        }
    )

    lines = format_issue_lines(issues)

    assert all(line.startswith("[") for line in lines)
    assert any("Missing required runtime key" in line for line in lines)


def test_f2p_008_runtime_report_has_expected_contract_shape() -> None:
    report = build_runtime_report(
        {
            "APP_ENV": "staging",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "sqlite:///db",
            "DEBUG": "false",
            "SESSION_COOKIE_SECURE": "true",
            "CSRF_COOKIE_SECURE": "true",
            "ALLOWED_HOSTS": "api.test.local",
            "CORS_ALLOWED_ORIGINS": "https://app.test.local",
        }
    )

    assert "environment" in report
    assert "safe" in report
    assert "score" in report
    assert "summary" in report
    assert "issues" in report
    assert "lines" in report
