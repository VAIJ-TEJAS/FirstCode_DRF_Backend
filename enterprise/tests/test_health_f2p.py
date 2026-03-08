from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase

from enterprise.health import (
    aggregate_status,
    build_liveness_payload,
    check_cache,
    check_clock,
    check_database,
    check_disk,
)


class HealthF2PTests(SimpleTestCase):
    def test_f2p_006_aggregate_status_down_has_priority(self):
        status = aggregate_status(["up", "degraded", "down"])
        self.assertEqual(status, "down")

    def test_f2p_007_aggregate_status_degraded_when_no_down_exists(self):
        status = aggregate_status(["up", "degraded", "up"])
        self.assertEqual(status, "degraded")

    def test_f2p_008_aggregate_status_up_when_all_components_up(self):
        status = aggregate_status(["up", "up", "up"])
        self.assertEqual(status, "up")

    def test_f2p_009_liveness_payload_contains_required_keys(self):
        payload = build_liveness_payload("backend-service")

        self.assertEqual(payload["service"], "backend-service")
        self.assertEqual(payload["status"], "up")
        self.assertIn("timestamp", payload)

    @mock.patch("enterprise.health.connection")
    def test_f2p_010_database_check_reports_up_for_successful_probe(self, mocked_connection):
        cursor_ctx = mock.MagicMock()
        mocked_connection.cursor.return_value.__enter__.return_value = cursor_ctx
        cursor_ctx.fetchone.return_value = (1,)

        payload = check_database()

        self.assertEqual(payload["status"], "up")
        self.assertIn("latency_ms", payload)
        self.assertIn("details", payload)

    @mock.patch("enterprise.health.cache")
    def test_f2p_011_cache_check_reports_degraded_on_probe_mismatch(self, mocked_cache):
        mocked_cache.get.return_value = "not-expected"

        payload = check_cache()

        self.assertEqual(payload["status"], "degraded")
        self.assertIn("details", payload)

    @mock.patch("enterprise.health.shutil.disk_usage")
    def test_f2p_012_disk_check_marks_down_when_free_space_is_low(self, mocked_disk_usage):
        mocked_disk_usage.return_value = (1000, 950, 50)

        payload = check_disk("/")

        self.assertEqual(payload["status"], "down")
        self.assertEqual(payload["path"], "/")

    def test_f2p_013_clock_check_returns_status_and_skew(self):
        payload = check_clock()

        self.assertIn(payload["status"], ["up", "degraded", "down"])
        self.assertIn("skew_proxy_ms", payload)
        self.assertIn("utc_now", payload)
