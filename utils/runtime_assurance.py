"""Runtime assurance helpers for production-safe deployment checks.

This module is intentionally framework-light so it can be validated quickly in
CI/evaluator environments without requiring a full Django initialization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class RuntimeRule:
    key: str
    expected: str
    severity: str
    message: str


@dataclass(frozen=True)
class RuntimeIssue:
    key: str
    severity: str
    message: str


MANDATORY_KEYS = [
    "APP_ENV",
    "DJANGO_SECRET_KEY",
    "DATABASE_URL",
]

RECOMMENDED_KEYS = [
    "ALLOWED_HOSTS",
    "CORS_ALLOWED_ORIGINS",
    "REDIS_URL",
    "SENTRY_DSN",
    "DEFAULT_FROM_EMAIL",
]

SAFETY_RULES = [
    RuntimeRule(
        key="DEBUG",
        expected="false",
        severity="error",
        message="DEBUG must be false in production environments.",
    ),
    RuntimeRule(
        key="SESSION_COOKIE_SECURE",
        expected="true",
        severity="warning",
        message="Session cookies should be secure in non-local deployments.",
    ),
    RuntimeRule(
        key="CSRF_COOKIE_SECURE",
        expected="true",
        severity="warning",
        message="CSRF cookies should be secure in non-local deployments.",
    ),
]


def normalize_environment(value: str | None) -> str:
    if not value:
        return "development"

    normalized = value.strip().lower()

    if normalized in {"dev", "development", "local"}:
        return "development"
    if normalized in {"stage", "staging", "preprod"}:
        return "staging"
    if normalized in {"prod", "production"}:
        return "production"

    return normalized


def _is_missing(value: str | None) -> bool:
    return value is None or not str(value).strip()


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _is_false(value: str | None) -> bool:
    if value is None:
        return False
    return str(value).strip().lower() in {"0", "false", "no", "off"}


def evaluate_runtime_environment(env: Dict[str, str | None]) -> List[RuntimeIssue]:
    issues: List[RuntimeIssue] = []

    for key in MANDATORY_KEYS:
        if _is_missing(env.get(key)):
            issues.append(
                RuntimeIssue(
                    key=key,
                    severity="error",
                    message=f"Missing required runtime key: {key}",
                )
            )

    for key in RECOMMENDED_KEYS:
        if _is_missing(env.get(key)):
            issues.append(
                RuntimeIssue(
                    key=key,
                    severity="warning",
                    message=f"Missing recommended runtime key: {key}",
                )
            )

    environment = normalize_environment(env.get("APP_ENV"))

    for rule in SAFETY_RULES:
        value = env.get(rule.key)

        if rule.expected == "true":
            is_match = _is_true(value)
        elif rule.expected == "false":
            is_match = _is_false(value)
        else:
            is_match = str(value).strip().lower() == rule.expected

        severity = rule.severity
        if environment != "production" and severity == "error":
            severity = "warning"

        if not is_match:
            issues.append(
                RuntimeIssue(
                    key=rule.key,
                    severity=severity,
                    message=rule.message,
                )
            )

    hosts = str(env.get("ALLOWED_HOSTS") or "")
    if "*" in hosts:
        issues.append(
            RuntimeIssue(
                key="ALLOWED_HOSTS",
                severity="error" if environment == "production" else "warning",
                message="Wildcard hosts are not allowed for hardened deployments.",
            )
        )

    return issues


def summarize_issues(issues: Iterable[RuntimeIssue]) -> Dict[str, int]:
    summary = {"error": 0, "warning": 0, "info": 0}

    for issue in issues:
        if issue.severity not in summary:
            summary[issue.severity] = 0
        summary[issue.severity] += 1

    return summary


def is_runtime_safe(issues: Iterable[RuntimeIssue]) -> bool:
    return all(issue.severity != "error" for issue in issues)


def format_issue_lines(issues: Iterable[RuntimeIssue]) -> List[str]:
    return [f"[{issue.severity}] {issue.key}: {issue.message}" for issue in issues]


def readiness_score(issues: Iterable[RuntimeIssue]) -> int:
    score = 100

    for issue in issues:
        if issue.severity == "error":
            score -= 20
        elif issue.severity == "warning":
            score -= 5
        else:
            score -= 1

    return max(0, score)


def build_runtime_report(env: Dict[str, str | None]) -> Dict[str, object]:
    issues = evaluate_runtime_environment(env)
    summary = summarize_issues(issues)

    return {
        "environment": normalize_environment(env.get("APP_ENV")),
        "safe": is_runtime_safe(issues),
        "score": readiness_score(issues),
        "summary": summary,
        "issues": [
            {
                "key": issue.key,
                "severity": issue.severity,
                "message": issue.message,
            }
            for issue in issues
        ],
        "lines": format_issue_lines(issues),
    }
