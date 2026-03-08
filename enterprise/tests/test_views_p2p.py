from __future__ import annotations

from unittest import mock

from django.test import TestCase
from rest_framework.test import APIRequestFactory

from enterprise.views import LivenessAPIView, ReadinessAPIView


class ViewP2PTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_p2p_005_liveness_endpoint_returns_200_and_expected_payload(self):
        request = self.factory.get("/health/live/")
        response = LivenessAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "up")
        self.assertIn("service", response.data)
        self.assertIn("timestamp", response.data)

    @mock.patch("enterprise.views.build_readiness_payload")
    def test_p2p_006_readiness_endpoint_returns_200_for_degraded_status(self, mocked_builder):
        mocked_builder.return_value = {
            "status": "degraded",
            "checked_at": "2026-01-01T00:00:00+00:00",
            "components": {
                "database": {"status": "up"},
                "cache": {"status": "degraded"},
                "disk": {"status": "up"},
                "clock": {"status": "up"},
                "config": {"status": "degraded"},
            },
        }

        request = self.factory.get("/health/ready/")
        response = ReadinessAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "degraded")

    @mock.patch("enterprise.views.build_readiness_payload")
    def test_p2p_007_readiness_endpoint_returns_503_for_down_status(self, mocked_builder):
        mocked_builder.return_value = {
            "status": "down",
            "checked_at": "2026-01-01T00:00:00+00:00",
            "components": {
                "database": {"status": "down"},
                "cache": {"status": "up"},
                "disk": {"status": "up"},
                "clock": {"status": "up"},
                "config": {"status": "up"},
            },
        }

        request = self.factory.get("/health/ready/")
        response = ReadinessAPIView.as_view()(request)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["status"], "down")

    @mock.patch("enterprise.views.build_readiness_payload")
    def test_p2p_008_readiness_endpoint_keeps_component_payload_shape(self, mocked_builder):
        mocked_builder.return_value = {
            "status": "up",
            "checked_at": "2026-01-01T00:00:00+00:00",
            "components": {
                "database": {"status": "up", "latency_ms": 10},
                "cache": {"status": "up", "latency_ms": 5},
                "disk": {"status": "up", "free_percent": 30},
                "clock": {"status": "up", "skew_proxy_ms": 9},
                "config": {
                    "status": "up",
                    "environment": "production",
                    "safe_mode": True,
                    "issues": [],
                    "is_ready": True,
                },
            },
        }

        request = self.factory.get("/health/ready/")
        response = ReadinessAPIView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("components", response.data)
        self.assertIn("config", response.data["components"])
        self.assertIn("issues", response.data["components"]["config"])
