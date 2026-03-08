from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase, override_settings

from enterprise.config import evaluate_runtime_config, serialize_config_report


class ConfigF2PTests(SimpleTestCase):
    @override_settings(
        DEBUG=False,
        ALLOWED_HOSTS=["api.example.com"],
        SECURE_SSL_REDIRECT=True,
        SESSION_COOKIE_SECURE=True,
        CSRF_COOKIE_SECURE=True,
        SECURE_CONTENT_TYPE_NOSNIFF=True,
        SECURE_BROWSER_XSS_FILTER=True,
        X_FRAME_OPTIONS="DENY",
    )
    @mock.patch.dict(
        "os.environ",
        {
            "APP_ENV": "production",
            "DJANGO_SECRET_KEY": "set",
            "DATABASE_URL": "postgres://test",
            "ALLOWED_HOSTS": "api.example.com",
            "CORS_ALLOWED_ORIGINS": "https://app.example.com",
            "SENTRY_DSN": "https://sentry-dsn",
            "REDIS_URL": "redis://cache:6379/0",
            "EMAIL_HOST": "smtp.example.com",
            "EMAIL_HOST_USER": "mailer",
            "DEFAULT_FROM_EMAIL": "noreply@example.com",
        },
        clear=True,
    )
    def test_f2p_001_config_is_ready_when_hardening_rules_are_met(self):
        report = evaluate_runtime_config()

        self.assertEqual(report.environment, "production")
        self.assertTrue(report.is_ready)
        self.assertTrue(report.safe_mode)
        self.assertEqual(report.issues, [])

    @override_settings(DEBUG=True, ALLOWED_HOSTS=["*"])
    @mock.patch.dict("os.environ", {"APP_ENV": "production"}, clear=True)
    def test_f2p_002_missing_required_env_vars_raise_errors(self):
        report = evaluate_runtime_config()

        self.assertFalse(report.is_ready)
        self.assertTrue(any(issue.key == "DJANGO_SECRET_KEY" and issue.severity == "error" for issue in report.issues))
        self.assertTrue(any(issue.key == "DATABASE_URL" and issue.severity == "error" for issue in report.issues))

    @override_settings(DEBUG=True, ALLOWED_HOSTS=["*"])
    @mock.patch.dict("os.environ", {"APP_ENV": "staging", "DJANGO_SECRET_KEY": "set", "DATABASE_URL": "sqlite:///db"}, clear=True)
    def test_f2p_003_non_production_violations_are_warnings(self):
        report = evaluate_runtime_config()

        self.assertEqual(report.environment, "staging")
        debug_issues = [issue for issue in report.issues if issue.key == "DEBUG"]
        self.assertGreaterEqual(len(debug_issues), 1)
        self.assertTrue(all(issue.severity == "warning" for issue in debug_issues))

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["api.example.com"], X_FRAME_OPTIONS="SAMEORIGIN")
    @mock.patch.dict("os.environ", {"APP_ENV": "production", "DJANGO_SECRET_KEY": "set", "DATABASE_URL": "sqlite:///db"}, clear=True)
    def test_f2p_004_serialize_config_report_keeps_issue_shape(self):
        report = evaluate_runtime_config()
        payload = serialize_config_report(report)

        self.assertIn("environment", payload)
        self.assertIn("safe_mode", payload)
        self.assertIn("is_ready", payload)
        self.assertIn("issues", payload)
        self.assertTrue(any(issue["key"] == "X_FRAME_OPTIONS" for issue in payload["issues"]))

    @override_settings(DEBUG=False, ALLOWED_HOSTS=["api.example.com"])
    @mock.patch.dict(
        "os.environ",
        {
            "APP_ENV": "dev",
            "DJANGO_SECRET_KEY": "dev-secret",
            "DATABASE_URL": "sqlite:///db",
        },
        clear=True,
    )
    def test_f2p_005_environment_aliases_are_normalized(self):
        report = evaluate_runtime_config()
        self.assertEqual(report.environment, "development")
