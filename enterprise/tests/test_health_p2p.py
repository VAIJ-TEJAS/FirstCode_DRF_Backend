from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase

from enterprise.health import build_readiness_payload


class HealthP2PTests(SimpleTestCase):
    @mock.patch("enterprise.health.evaluate_runtime_config")
    @mock.patch("enterprise.health.check_clock")
    @mock.patch("enterprise.health.check_disk")
    @mock.patch("enterprise.health.check_cache")
    @mock.patch("enterprise.health.check_database")
    def test_p2p_001_readiness_reports_up_when_all_components_are_up(
        self,
        mocked_db,
        mocked_cache,
        mocked_disk,
        mocked_clock,
        mocked_config,
    ):
        mocked_db.return_value = {"status": "up", "latency_ms": 20, "details": "ok"}
        mocked_cache.return_value = {"status": "up", "latency_ms": 8, "details": "ok"}
        mocked_disk.return_value = {"status": "up", "free_percent": 42, "path": "/", "details": "ok"}
        mocked_clock.return_value = {"status": "up", "utc_now": "2026-01-01T00:00:00+00:00", "skew_proxy_ms": 12, "details": "ok"}
        mocked_config.return_value = mock.Mock(is_ready=True, environment="production", safe_mode=True, issues=[])

        payload = build_readiness_payload()

        self.assertEqual(payload["status"], "up")
        self.assertIn("components", payload)
        self.assertEqual(payload["components"]["config"]["status"], "up")

    @mock.patch("enterprise.health.evaluate_runtime_config")
    @mock.patch("enterprise.health.check_clock")
    @mock.patch("enterprise.health.check_disk")
    @mock.patch("enterprise.health.check_cache")
    @mock.patch("enterprise.health.check_database")
    def test_p2p_002_readiness_reports_degraded_when_config_is_not_ready(
        self,
        mocked_db,
        mocked_cache,
        mocked_disk,
        mocked_clock,
        mocked_config,
    ):
        mocked_db.return_value = {"status": "up", "latency_ms": 20, "details": "ok"}
        mocked_cache.return_value = {"status": "up", "latency_ms": 8, "details": "ok"}
        mocked_disk.return_value = {"status": "up", "free_percent": 42, "path": "/", "details": "ok"}
        mocked_clock.return_value = {"status": "up", "utc_now": "2026-01-01T00:00:00+00:00", "skew_proxy_ms": 12, "details": "ok"}
        mocked_config.return_value = mock.Mock(
            is_ready=False,
            environment="production",
            safe_mode=False,
            issues=[mock.Mock(key="DEBUG", severity="error", message="debug on")],
        )

        payload = build_readiness_payload()

        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["components"]["config"]["status"], "degraded")

    @mock.patch("enterprise.health.evaluate_runtime_config")
    @mock.patch("enterprise.health.check_clock")
    @mock.patch("enterprise.health.check_disk")
    @mock.patch("enterprise.health.check_cache")
    @mock.patch("enterprise.health.check_database")
    def test_p2p_003_readiness_reports_down_when_any_runtime_probe_is_down(
        self,
        mocked_db,
        mocked_cache,
        mocked_disk,
        mocked_clock,
        mocked_config,
    ):
        mocked_db.return_value = {"status": "down", "latency_ms": None, "details": "db timeout"}
        mocked_cache.return_value = {"status": "up", "latency_ms": 8, "details": "ok"}
        mocked_disk.return_value = {"status": "up", "free_percent": 42, "path": "/", "details": "ok"}
        mocked_clock.return_value = {"status": "up", "utc_now": "2026-01-01T00:00:00+00:00", "skew_proxy_ms": 12, "details": "ok"}
        mocked_config.return_value = mock.Mock(is_ready=True, environment="production", safe_mode=True, issues=[])

        payload = build_readiness_payload()

        self.assertEqual(payload["status"], "down")
        self.assertEqual(payload["components"]["database"]["status"], "down")

    @mock.patch("enterprise.health.evaluate_runtime_config")
    @mock.patch("enterprise.health.check_clock")
    @mock.patch("enterprise.health.check_disk")
    @mock.patch("enterprise.health.check_cache")
    @mock.patch("enterprise.health.check_database")
    def test_p2p_004_readiness_payload_contains_expected_component_schema(
        self,
        mocked_db,
        mocked_cache,
        mocked_disk,
        mocked_clock,
        mocked_config,
    ):
        mocked_db.return_value = {"status": "up", "latency_ms": 10, "details": "ok"}
        mocked_cache.return_value = {"status": "degraded", "latency_ms": 80, "details": "slow"}
        mocked_disk.return_value = {"status": "up", "free_percent": 28.2, "path": "/", "details": "ok"}
        mocked_clock.return_value = {"status": "up", "utc_now": "2026-01-01T00:00:00+00:00", "skew_proxy_ms": 15, "details": "ok"}
        mocked_config.return_value = mock.Mock(
            is_ready=True,
            environment="staging",
            safe_mode=True,
            issues=[mock.Mock(key="SENTRY_DSN", severity="warning", message="missing")],
        )

        payload = build_readiness_payload()

        self.assertIn("checked_at", payload)
        self.assertIn("components", payload)
        for key in ["database", "cache", "disk", "clock", "config"]:
            self.assertIn(key, payload["components"])
            self.assertIn("status", payload["components"][key])
