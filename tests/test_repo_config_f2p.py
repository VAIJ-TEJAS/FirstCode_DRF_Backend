from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvIssue:
    key: str
    severity: str
    message: str


def evaluate_env(env: dict[str, str]) -> tuple[bool, list[EnvIssue]]:
    mandatory = ["APP_ENV", "DJANGO_SECRET_KEY", "DATABASE_URL"]
    recommended = ["ALLOWED_HOSTS", "CORS_ALLOWED_ORIGINS", "REDIS_URL", "SENTRY_DSN"]

    issues: list[EnvIssue] = []

    for key in mandatory:
        if not env.get(key, "").strip():
            issues.append(EnvIssue(key=key, severity="error", message=f"Missing required key {key}"))

    for key in recommended:
        if not env.get(key, "").strip():
            issues.append(EnvIssue(key=key, severity="warning", message=f"Missing recommended key {key}"))

    environment = env.get("APP_ENV", "development").strip().lower()

    if environment in {"production", "prod"}:
        if env.get("DEBUG", "false").lower() in {"1", "true", "yes", "on"}:
            issues.append(EnvIssue(key="DEBUG", severity="error", message="DEBUG must be disabled in production"))

        hosts = env.get("ALLOWED_HOSTS", "")
        if "*" in hosts:
            issues.append(EnvIssue(key="ALLOWED_HOSTS", severity="error", message="Wildcard hosts are not allowed in production"))

    return (not any(issue.severity == "error" for issue in issues), issues)


def test_f2p_001_env_is_safe_with_required_values_present() -> None:
    safe, issues = evaluate_env(
        {
            "APP_ENV": "staging",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "sqlite:///db.sqlite3",
            "ALLOWED_HOSTS": "api.test.local",
            "CORS_ALLOWED_ORIGINS": "https://app.test.local",
        }
    )

    assert safe is True
    assert all(issue.severity != "error" for issue in issues)


def test_f2p_002_missing_mandatory_values_are_errors() -> None:
    safe, issues = evaluate_env({"APP_ENV": "production"})

    assert safe is False
    assert any(issue.key == "DJANGO_SECRET_KEY" and issue.severity == "error" for issue in issues)
    assert any(issue.key == "DATABASE_URL" and issue.severity == "error" for issue in issues)


def test_f2p_003_missing_recommended_values_are_warnings() -> None:
    safe, issues = evaluate_env(
        {
            "APP_ENV": "staging",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "sqlite:///db.sqlite3",
        }
    )

    assert safe is True
    assert any(issue.key == "REDIS_URL" and issue.severity == "warning" for issue in issues)


def test_f2p_004_production_debug_true_is_error() -> None:
    safe, issues = evaluate_env(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "true",
            "ALLOWED_HOSTS": "api.example.com",
        }
    )

    assert safe is False
    assert any(issue.key == "DEBUG" and issue.severity == "error" for issue in issues)


def test_f2p_005_production_wildcard_hosts_is_error() -> None:
    safe, issues = evaluate_env(
        {
            "APP_ENV": "prod",
            "DJANGO_SECRET_KEY": "secret",
            "DATABASE_URL": "postgres://db",
            "DEBUG": "false",
            "ALLOWED_HOSTS": "*",
        }
    )

    assert safe is False
    assert any(issue.key == "ALLOWED_HOSTS" and issue.severity == "error" for issue in issues)


def test_f2p_006_environment_values_can_be_pulled_from_os_environ() -> None:
    env = dict(os.environ)

    safe, issues = evaluate_env(env)

    assert isinstance(safe, bool)
    assert isinstance(issues, list)


def test_f2p_007_warning_and_error_counts_can_be_derived() -> None:
    _, issues = evaluate_env(
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "",
            "DATABASE_URL": "",
            "ALLOWED_HOSTS": "*",
            "DEBUG": "true",
        }
    )

    warning_count = sum(1 for issue in issues if issue.severity == "warning")
    error_count = sum(1 for issue in issues if issue.severity == "error")

    assert error_count >= 3
    assert warning_count >= 1


def test_f2p_008_messages_are_human_readable_for_ci_logs() -> None:
    _, issues = evaluate_env({"APP_ENV": "production"})

    rendered = [f"[{issue.severity}] {issue.key}: {issue.message}" for issue in issues]

    assert all("[" in line and "]" in line for line in rendered)
    assert any("Missing required key" in line for line in rendered)
