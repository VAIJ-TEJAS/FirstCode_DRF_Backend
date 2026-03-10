from __future__ import annotations

from utils.runtime_assurance import build_runtime_report


def test_p2p_1821_runtime_report_flags_missing_keys() -> None:
    report = build_runtime_report({"APP_ENV": "production", "DEBUG": "false"})
    assert report["summary"]["error"] >= 2


def test_p2p_1822_runtime_report_safe_when_keys_present() -> None:
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
