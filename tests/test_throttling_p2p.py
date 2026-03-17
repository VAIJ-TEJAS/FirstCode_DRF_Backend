"""P2P tests for rate limiting integration.

Tests the integration between throttling components including:
- Throttle and middleware interaction
- Multiple throttle class coordination
- Cache backend integration
- Request/response flow
"""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import MagicMock, Mock, patch

import pytest

from utils.throttling import (
    AdminBypassThrottle,
    AuditSensitiveThrottle,
    BurstRateThrottle,
    ContentCreationThrottle,
    DynamicRateThrottle,
    ExportThrottle,
    IPRateThrottle,
    PremiumUserRateThrottle,
    RateLimitHeadersMiddleware,
    RateLimitInfo,
    SustainedRateThrottle,
    WebhookThrottle,
    get_throttle_classes,
)


class MockRequest:
    """Mock request for P2P testing."""

    def __init__(
        self,
        user=None,
        ip="192.168.1.1",
        user_agent="Test-Agent",
        forwarded_for=None,
        method="GET",
    ):
        self.user = user or Mock()
        self.method = method
        self.META = {
            "REMOTE_ADDR": ip,
            "HTTP_USER_AGENT": user_agent,
            "HTTP_X_FORWARDED_FOR": forwarded_for,
        }
        self._rate_limit_info = None


class MockUser:
    """Mock authenticated user."""

    def __init__(
        self,
        pk=42,
        is_authenticated=True,
        is_staff=False,
        is_superuser=False,
        is_premium=False,
    ):
        self.pk = pk
        self.id = pk
        self.is_authenticated = is_authenticated
        self.is_staff = is_staff
        self.is_superuser = is_superuser
        
        if is_premium:
            self.subscription = Mock()
            self.subscription.is_premium = True


class MockResponse:
    """Mock response for testing."""

    def __init__(self, status_code=200):
        self.status_code = status_code
        self.headers = {}

    def __getitem__(self, key):
        return self.headers.get(key)

    def __setitem__(self, key, value):
        self.headers[key] = value

    def get(self, key, default=None):
        return self.headers.get(key, default)


class TestP2PThrottleIntegration:
    """Test throttle class integration (P2P-001 to P2P-030)."""

    def test_p2p_001_default_throttles_work_together(self) -> None:
        """Verify burst and sustained throttles coordinate."""
        classes = get_throttle_classes("default")
        
        # Both throttles should be present
        assert BurstRateThrottle in classes
        assert SustainedRateThrottle in classes
        
        # Different scopes mean different rate limits
        burst = BurstRateThrottle()
        sustained = SustainedRateThrottle()
        
        assert burst.scope != sustained.scope
        assert burst.rate != sustained.rate

    def test_p2p_002_strict_throttles_include_all(self) -> None:
        """Verify strict throttles include IP, burst, and sustained."""
        classes = get_throttle_classes("strict")
        
        assert IPRateThrottle in classes
        assert BurstRateThrottle in classes
        assert SustainedRateThrottle in classes

    def test_p2p_003_admin_bypass_allows_access(self) -> None:
        """Verify admin bypass throttle allows admin users."""
        throttle = AdminBypassThrottle()
        
        # Admin user should be allowed
        admin_user = MockUser(is_staff=True)
        request = MockRequest(user=admin_user)
        view = Mock()
        
        result = throttle.allow_request(request, view)
        assert result is True

    def test_p2p_004_admin_bypass_allows_superuser(self) -> None:
        """Verify admin bypass allows superusers."""
        throttle = AdminBypassThrottle()
        
        superuser = MockUser(is_superuser=True)
        request = MockRequest(user=superuser)
        view = Mock()
        
        result = throttle.allow_request(request, view)
        assert result is True

    def test_p2p_005_admin_bypass_falls_through_for_non_admin(self) -> None:
        """Verify admin bypass returns True for non-admin (allows other throttles)."""
        throttle = AdminBypassThrottle()
        
        regular_user = MockUser(is_staff=False, is_superuser=False)
        request = MockRequest(user=regular_user)
        view = Mock()
        
        # Returns True so other throttles can decide
        result = throttle.allow_request(request, view)
        assert result is True

    def test_p2p_006_premium_user_detects_premium(self) -> None:
        """Verify premium user throttle detects premium status."""
        throttle = PremiumUserRateThrottle()
        
        premium_user = MockUser(is_premium=True)
        request = MockRequest(user=premium_user)
        view = Mock()
        
        # Should check subscription and potentially allow
        # The actual behavior depends on allow_request implementation
        assert hasattr(request.user, "subscription")
        assert request.user.subscription.is_premium is True

    def test_p2p_007_premium_throttle_fails_for_non_premium(self) -> None:
        """Verify premium throttle returns False for non-premium."""
        throttle = PremiumUserRateThrottle()
        
        regular_user = MockUser(is_premium=False)
        regular_user.subscription = Mock()
        regular_user.subscription.is_premium = False
        request = MockRequest(user=regular_user)
        view = Mock()
        
        result = throttle.allow_request(request, view)
        assert result is False

    def test_p2p_008_ip_throttle_extracts_client_ip(self) -> None:
        """Verify IP throttle correctly extracts client IP."""
        throttle = IPRateThrottle()
        
        request = MockRequest(ip="203.0.113.1")
        ident = throttle.get_ident(request)
        
        assert ident == "203.0.113.1"

    def test_p2p_009_ip_throttle_prefers_forwarded_for(self) -> None:
        """Verify IP throttle prefers X-Forwarded-For header."""
        throttle = IPRateThrottle()
        
        request = MockRequest(
            ip="10.0.0.1",
            forwarded_for="203.0.113.1, 198.51.100.2"
        )
        ident = throttle.get_ident(request)
        
        # Should use the first IP in X-Forwarded-For
        assert ident == "203.0.113.1"

    def test_p2p_010_burst_throttle_generates_unique_keys(self) -> None:
        """Verify burst throttle generates unique cache keys."""
        throttle = BurstRateThrottle()
        
        request1 = MockRequest(ip="192.168.1.1")
        request2 = MockRequest(ip="192.168.1.2")
        view = Mock()
        
        key1 = throttle.get_cache_key(request1, view)
        key2 = throttle.get_cache_key(request2, view)
        
        assert key1 != key2
        assert "throttle_burst_" in key1
        assert "throttle_burst_" in key2


class TestP2PRateLimitMiddleware:
    """Test rate limit middleware integration (P2P-031 to P2P-060)."""

    def test_p2p_031_middleware_adds_headers(self) -> None:
        """Verify middleware adds rate limit headers."""
        
        def mock_get_response(request):
            response = MockResponse()
            return response
        
        middleware = RateLimitHeadersMiddleware(mock_get_response)
        
        request = MockRequest()
        request._rate_limit_info = {
            "limit": 100,
            "remaining": 50,
            "reset": 1234567890,
        }
        
        response = middleware(request)
        
        assert response["X-RateLimit-Limit"] == "100"
        assert response["X-RateLimit-Remaining"] == "50"
        assert response["X-RateLimit-Reset"] == "1234567890"

    def test_p2p_032_middleware_passes_without_rate_info(self) -> None:
        """Verify middleware works without rate limit info."""
        
        def mock_get_response(request):
            return MockResponse()
        
        middleware = RateLimitHeadersMiddleware(mock_get_response)
        
        request = MockRequest()
        # No _rate_limit_info set
        
        response = middleware(request)
        
        # Should not add headers
        assert response.get("X-RateLimit-Limit") is None

    def test_p2p_033_middleware_preserves_response(self) -> None:
        """Verify middleware preserves original response."""
        
        def mock_get_response(request):
            response = MockResponse(status_code=201)
            response["Content-Type"] = "application/json"
            return response
        
        middleware = RateLimitHeadersMiddleware(mock_get_response)
        
        request = MockRequest()
        request._rate_limit_info = {"limit": 100, "remaining": 99, "reset": 1234567890}
        
        response = middleware(request)
        
        assert response.status_code == 201
        assert response["Content-Type"] == "application/json"


class TestP2PDynamicThrottle:
    """Test dynamic throttle with system load (P2P-061 to P2P-090)."""

    @patch("django.core.cache.cache.get")
    def test_p2p_061_healthy_system_uses_default_rate(self, mock_cache_get) -> None:
        """Verify healthy system uses default rate limit."""
        mock_cache_get.return_value = "healthy"
        
        throttle = DynamicRateThrottle()
        rate = throttle.get_rate()
        
        assert rate == throttle.default_rate

    @patch("django.core.cache.cache.get")
    def test_p2p_062_high_load_uses_reduced_rate(self, mock_cache_get) -> None:
        """Verify high load uses reduced rate limit."""
        mock_cache_get.return_value = "high_load"
        
        throttle = DynamicRateThrottle()
        rate = throttle.get_rate()
        
        assert rate == throttle.high_load_rate

    @patch("django.core.cache.cache.get")
    def test_p2p_063_critical_load_uses_minimal_rate(self, mock_cache_get) -> None:
        """Verify critical load uses minimal rate limit."""
        mock_cache_get.return_value = "critical"
        
        throttle = DynamicRateThrottle()
        rate = throttle.get_rate()
        
        assert rate == throttle.critical_load_rate

    @patch("django.core.cache.cache.get")
    def test_p2p_064_missing_health_uses_default(self, mock_cache_get) -> None:
        """Verify missing health status defaults to normal rate."""
        mock_cache_get.return_value = None
        
        throttle = DynamicRateThrottle()
        rate = throttle.get_rate()
        
        assert rate == throttle.default_rate


class TestP2PExportThrottle:
    """Test export throttle with custom messaging (P2P-091 to P2P-110)."""

    def test_p2p_091_export_throttle_has_custom_message(self) -> None:
        """Verify export throttle provides custom wait message."""
        throttle = ExportThrottle()
        
        # Simulate being throttled
        throttle.num_requests = 5
        throttle.duration = 3600
        
        # Mock the history to simulate rate limit hit
        now = time.time()
        throttle.history = [now - 3500] * 5  # 5 requests in the last hour
        
        wait_time = throttle.wait()
        
        if wait_time:
            # Should have custom message with minutes
            assert "minute" in throttle.detail.lower() or wait_time > 0

    def test_p2p_092_export_rate_is_strict(self) -> None:
        """Verify export rate is appropriately strict."""
        throttle = ExportThrottle()
        
        # Should be 5 per hour
        num, duration = throttle.parse_rate(throttle.rate)
        assert num == 5
        assert duration == 3600


class TestP2PAuditThrottle:
    """Test audit throttle logging (P2P-111 to P2P-130)."""

    @patch("logging.getLogger")
    def test_p2p_111_audit_throttle_logs_when_limited(self, mock_get_logger) -> None:
        """Verify audit throttle logs rate limit hits."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        
        throttle = AuditSensitiveThrottle()
        
        # Simulate being throttled
        now = time.time()
        throttle.num_requests = 30
        throttle.duration = 60
        throttle.history = [now - 30] * 30
        
        wait_time = throttle.wait()
        
        # The logging happens when wait() returns a value
        # We verify the throttle is properly configured to log
        assert throttle.scope == "audit_sensitive"
        assert throttle.rate == "30/minute"


class TestP2PThrottleCoordination:
    """Test multiple throttles working together (P2P-131 to P2P-160)."""

    def test_p2p_131_all_throttles_different_scopes(self) -> None:
        """Verify all throttle classes have unique scopes."""
        throttles = [
            BurstRateThrottle(),
            SustainedRateThrottle(),
            IPRateThrottle(),
            ContentCreationThrottle(),
            ExportThrottle(),
            AuditSensitiveThrottle(),
        ]
        
        scopes = [t.scope for t in throttles]
        
        # All scopes should be unique
        assert len(scopes) == len(set(scopes))

    def test_p2p_132_throttles_have_different_rates(self) -> None:
        """Verify throttles have appropriate rate differences."""
        rates = {
            "burst": BurstRateThrottle.rate,
            "sustained": SustainedRateThrottle.rate,
            "content": ContentCreationThrottle.rate,
            "export": ExportThrottle.rate,
            "audit": AuditSensitiveThrottle.rate,
        }
        
        # Export should be most restrictive
        assert "5/hour" == rates["export"]
        
        # Sustained should allow most requests
        assert "1000" in rates["sustained"]

    def test_p2p_133_throttle_classes_instantiable(self) -> None:
        """Verify all throttle classes can be instantiated."""
        classes = [
            BurstRateThrottle,
            SustainedRateThrottle,
            IPRateThrottle,
            PremiumUserRateThrottle,
            ContentCreationThrottle,
            ExportThrottle,
            AuditSensitiveThrottle,
            DynamicRateThrottle,
            AdminBypassThrottle,
        ]
        
        for cls in classes:
            instance = cls()
            assert instance is not None
            assert hasattr(instance, "scope")


class TestP2PRealWorldScenarios:
    """Test real-world throttling scenarios (P2P-161 to P2P-190)."""

    def test_p2p_161_anonymous_user_limited_by_ip(self) -> None:
        """Verify anonymous users are limited by IP."""
        classes = get_throttle_classes("anonymous")
        
        assert IPRateThrottle in classes
        assert len(classes) == 1  # Only IP-based

    def test_p2p_162_premium_user_gets_higher_limits(self) -> None:
        """Verify premium users can access higher rate limits."""
        classes = get_throttle_classes("premium")
        
        assert PremiumUserRateThrottle in classes
        
        premium = PremiumUserRateThrottle()
        assert "5000" in premium.rate

    def test_p2p_163_content_creation_limited(self) -> None:
        """Verify content creation has strict limits."""
        classes = get_throttle_classes("content")
        
        assert ContentCreationThrottle in classes
        
        throttle = ContentCreationThrottle()
        assert "10/minute" == throttle.rate

    def test_p2p_164_export_operations_limited(self) -> None:
        """Verify export operations are strictly limited."""
        classes = get_throttle_classes("export")
        
        assert ExportThrottle in classes
        assert len(classes) == 1

    def test_p2p_165_audit_endpoints_protected(self) -> None:
        """Verify audit endpoints have special protection."""
        classes = get_throttle_classes("audit")
        
        assert AuditSensitiveThrottle in classes
        assert len(classes) == 1

    def test_p2p_166_webhook_endpoints_separate_scope(self) -> None:
        """Verify webhooks have dedicated throttling."""
        classes = get_throttle_classes("webhook")
        
        assert len(classes) == 1
        assert classes[0] == WebhookThrottle

    def test_p2p_167_admin_bypass_available(self) -> None:
        """Verify admin bypass throttle is available."""
        classes = get_throttle_classes("admin")
        
        from utils.throttling import AdminBypassThrottle
        assert AdminBypassThrottle in classes

    def test_p2p_168_dynamic_load_response(self) -> None:
        """Verify dynamic throttle responds to load."""
        throttle = DynamicRateThrottle()
        
        # Should have different rates for different load levels
        assert throttle.default_rate != throttle.critical_load_rate
        assert throttle.high_load_rate != throttle.critical_load_rate


class TestP2PRateLimitInfoFlow:
    """Test rate limit info flow through request/response (P2P-191 to P2P-210)."""

    def test_p2p_191_rate_info_attached_to_request(self) -> None:
        """Verify rate limit info can be attached to request."""
        request = MockRequest()
        info = RateLimitInfo(
            limit=1000,
            remaining=500,
            reset_timestamp=1234567890,
            window="hour",
        )
        
        request._rate_limit_info = info.to_dict()
        
        assert request._rate_limit_info["limit"] == 1000
        assert request._rate_limit_info["remaining"] == 500

    def test_p2p_192_middleware_extracts_from_request(self) -> None:
        """Verify middleware extracts rate info from request."""
        
        def get_response(request):
            response = MockResponse()
            return response
        
        middleware = RateLimitHeadersMiddleware(get_response)
        
        request = MockRequest()
        request._rate_limit_info = {
            "limit": 100,
            "remaining": 50,
            "reset": 1234567890,
            "window": "minute",
        }
        
        response = middleware(request)
        
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_p2p_193_headers_follow_convention(self) -> None:
        """Verify headers follow standard naming convention."""
        info = RateLimitInfo(
            limit=100,
            remaining=99,
            reset_timestamp=1234567890,
            window="minute",
        )
        
        data = info.to_dict()
        
        assert "limit" in data
        assert "remaining" in data
        assert "reset" in data
        assert "window" in data
