from __future__ import annotations

from utils.runtime_assurance import build_runtime_report


def test_p2p_1721_runtime_report_flags_missing_recommended_keys() -> None:
    report = build_runtime_report({
        "APP_ENV": "staging",
        "DJANGO_SECRET_KEY": "x",
        "DATABASE_URL": "postgres://db",
        "DEBUG": "false",
    })

    assert report["summary"]["warning"] >= 1
    assert report["environment"] == "staging"


def test_p2p_1722_runtime_report_is_safe_when_required_keys_present() -> None:
    report = build_runtime_report({
        "APP_ENV": "production",
        "DJANGO_SECRET_KEY": "x",
        "DATABASE_URL": "postgres://db",
        "DEBUG": "false",
        "SESSION_COOKIE_SECURE": "true",
        "CSRF_COOKIE_SECURE": "true",
        "ALLOWED_HOSTS": "api.example.com",
    })

    assert report["safe"] is True
