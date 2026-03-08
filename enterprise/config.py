"""Runtime configuration evaluation helpers.

This module does not mutate Django settings. It only inspects current runtime
state and returns a report that can be used by readiness endpoints or startup
checks.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from enterprise.constants import MANDATORY_ENV_VARS, PRODUCTION_SAFETY_RULES, RECOMMENDED_ENV_VARS


@dataclass(frozen=True)
class ConfigIssue:
    key: str
    severity: str
    message: str


@dataclass(frozen=True)
class ConfigReport:
    environment: str
    safe_mode: bool
    issues: list[ConfigIssue]

    @property
    def is_ready(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)


def _normalize_environment(value: str | None) -> str:
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


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on", "enabled"}:
            return True
        if normalized in {"0", "false", "no", "off", "disabled"}:
            return False
    return default


def _is_missing(value: str | None) -> bool:
    return value is None or not str(value).strip()


def evaluate_runtime_config() -> ConfigReport:
    env_name = _normalize_environment(os.getenv("APP_ENV") or os.getenv("ENVIRONMENT"))
    issues: list[ConfigIssue] = []

    for env_var in MANDATORY_ENV_VARS:
        if _is_missing(os.getenv(env_var)):
            issues.append(
                ConfigIssue(
                    key=env_var,
                    severity="error",
                    message=f"Missing mandatory env var: {env_var}",
                )
            )

    for env_var in RECOMMENDED_ENV_VARS:
        if _is_missing(os.getenv(env_var)):
            issues.append(
                ConfigIssue(
                    key=env_var,
                    severity="warning",
                    message=f"Recommended env var is not set: {env_var}",
                )
            )

    # Production-specific safety rules are warnings in non-prod and errors in prod.
    is_prod = env_name == "production"
    severity_if_violation = "error" if is_prod else "warning"

    for setting_key, expected_value in PRODUCTION_SAFETY_RULES.items():
        current_value = getattr(settings, setting_key, None)

        if setting_key == "X_FRAME_OPTIONS":
            matches = str(current_value).upper() == str(expected_value).upper()
        elif isinstance(expected_value, bool):
            matches = _as_bool(current_value, default=False) == expected_value
        else:
            matches = current_value == expected_value

        if not matches:
            issues.append(
                ConfigIssue(
                    key=setting_key,
                    severity=severity_if_violation,
                    message=f"{setting_key} should be set to {expected_value} for hardened deployments.",
                )
            )

    debug_enabled = _as_bool(getattr(settings, "DEBUG", None), default=True)
    if debug_enabled:
        issues.append(
            ConfigIssue(
                key="DEBUG",
                severity="error" if is_prod else "warning",
                message="DEBUG mode is enabled. Disable it for production-grade deployment.",
            )
        )

    allowed_hosts = getattr(settings, "ALLOWED_HOSTS", []) or []
    if "*" in allowed_hosts:
        issues.append(
            ConfigIssue(
                key="ALLOWED_HOSTS",
                severity="error" if is_prod else "warning",
                message="ALLOWED_HOSTS contains wildcard '*'. Use explicit hostnames.",
            )
        )

    safe_mode = not any(issue.severity == "error" for issue in issues)

    return ConfigReport(environment=env_name, safe_mode=safe_mode, issues=issues)


def serialize_config_report(report: ConfigReport) -> dict[str, Any]:
    return {
        "environment": report.environment,
        "safe_mode": report.safe_mode,
        "is_ready": report.is_ready,
        "issues": [
            {
                "key": issue.key,
                "severity": issue.severity,
                "message": issue.message,
            }
            for issue in report.issues
        ],
    }
