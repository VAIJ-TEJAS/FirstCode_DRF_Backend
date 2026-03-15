"""Rate limiting and throttling configuration for enterprise API protection.

Provides comprehensive rate limiting strategies including:
- User-based rate limiting
- IP-based rate limiting
- Endpoint-specific rate limiting
- Burst and sustained rate controls
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Set

from django.core.cache import cache
from django.http import HttpRequest
from rest_framework.throttling import (
    AnonRateThrottle,
    BaseThrottle,
    ScopedRateThrottle,
    UserRateThrottle,
)
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


class BurstRateThrottle(UserRateThrottle):
    """Burst rate limiting for short-term high-traffic scenarios.
    
    Allows short bursts of requests with a smaller window.
    Default: 20 requests per minute
    """
    
    scope = "burst"
    rate = "20/minute"
    
    def get_cache_key(self, request: HttpRequest, view: APIView) -> str:
        """Generate cache key including user identification."""
        ident = self.get_ident(request)
        return f"throttle_burst_{ident}"


class SustainedRateThrottle(UserRateThrottle):
    """Sustained rate limiting for long-term API usage.
    
    Controls overall API usage over a longer window.
    Default: 1000 requests per hour
    """
    
    scope = "sustained"
    rate = "1000/hour"
    
    def get_cache_key(self, request: HttpRequest, view: APIView) -> str:
        """Generate cache key including user identification."""
        ident = self.get_ident(request)
        return f"throttle_sustained_{ident}"


class IPRateThrottle(AnonRateThrottle):
    """IP-based rate limiting for anonymous requests.
    
    Protects against abuse from specific IP addresses.
    Default: 100 requests per hour per IP
    """
    
    scope = "ip"
    rate = "100/hour"
    
    def get_ident(self, request: HttpRequest) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            # Get the first IP in the chain (client IP)
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class EndpointRateThrottle(ScopedRateThrottle):
    """Endpoint-specific rate limiting.
    
    Allows different rate limits for different API endpoints.
    Configure rates in REST_FRAMEWORK settings.
    """
    
    def get_cache_key(self, request: HttpRequest, view: APIView) -> str:
        """Generate scoped cache key."""
        ident = self.get_ident(request)
        scope = getattr(view, "throttle_scope", None)
        if scope:
            return f"throttle_{scope}_{ident}"
        return f"throttle_endpoint_{ident}"


class PremiumUserRateThrottle(UserRateThrottle):
    """Higher rate limits for premium/paid users.
    
    Checks user subscription tier to determine rate limit.
    Default: 5000 requests per hour for premium users
    """
    
    scope = "premium"
    rate = "5000/hour"
    
    def allow_request(self, request: HttpRequest, view: APIView) -> bool:
        """Check if user has premium access."""
        if not request.user or not request.user.is_authenticated:
            return False
        
        # Check if user has premium subscription
        # This would integrate with subscription system
        if hasattr(request.user, "subscription"):
            if request.user.subscription.is_premium:
                return super().allow_request(request, view)
        
        # Fall back to standard throttle
        return True


class AdminBypassThrottle(BaseThrottle):
    """Throttle that bypasses rate limiting for admin users.
    
    Allows admin users unlimited API access.
    """
    
    def allow_request(self, request: HttpRequest, view: APIView) -> bool:
        """Always allow admin users."""
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True
        return True  # Allow other throttles to decide


class AuditSensitiveThrottle(UserRateThrottle):
    """Strict rate limiting for audit-sensitive endpoints.
    
    Applies stricter limits to endpoints that modify audit logs
    or access sensitive audit data.
    Default: 30 requests per minute
    """
    
    scope = "audit_sensitive"
    rate = "30/minute"
    
    def wait(self) -> Optional[float]:
        """Return wait time with logging."""
        wait_time = super().wait()
        if wait_time:
            logger.warning(f"Audit-sensitive endpoint rate limit hit, wait: {wait_time}s")
        return wait_time


class ContentCreationThrottle(UserRateThrottle):
    """Rate limiting for content creation endpoints.
    
    Prevents spam content creation while allowing legitimate use.
    Default: 10 creations per minute
    """
    
    scope = "content_creation"
    rate = "10/minute"


class ExportThrottle(UserRateThrottle):
    """Rate limiting for data export endpoints.
    
    Prevents abuse of resource-intensive export operations.
    Default: 5 exports per hour
    """
    
    scope = "export"
    rate = "5/hour"
    
    def wait(self) -> Optional[float]:
        """Return wait time with user-friendly message."""
        wait_time = super().wait()
        if wait_time:
            minutes = int(wait_time // 60)
            self.detail = f"Export limit reached. Please wait {minutes} minutes before next export."
        return wait_time


class WebhookThrottle(AnonRateThrottle):
    """Rate limiting for webhook endpoints.
    
    Protects webhook receivers from being overwhelmed.
    Default: 60 requests per minute per source IP
    """
    
    scope = "webhook"
    rate = "60/minute"
    
    def get_ident(self, request: HttpRequest) -> str:
        """Identify by webhook source when available."""
        # Check for webhook signature or source identifier
        webhook_id = request.META.get("HTTP_X_WEBHOOK_ID")
        if webhook_id:
            return f"webhook_{webhook_id}"
        return super().get_ident(request)


class DynamicRateThrottle(BaseThrottle):
    """Dynamic rate limiting based on system load.
    
    Automatically adjusts rate limits based on system health metrics.
    """
    
    default_rate = "100/minute"
    high_load_rate = "50/minute"
    critical_load_rate = "20/minute"
    
    def __init__(self) -> None:
        self.rate = self.default_rate
        
    def get_rate(self) -> str:
        """Determine current rate based on system load."""
        # Check system health metrics from cache
        health_status = cache.get("system_health_status", "healthy")
        
        if health_status == "critical":
            return self.critical_load_rate
        elif health_status == "high_load":
            return self.high_load_rate
        return self.default_rate
    
    def parse_rate(self, rate: str) -> tuple[int, int]:
        """Parse rate string into (num_requests, duration)."""
        if rate is None:
            return (None, None)
        
        num, period = rate.split("/")
        num_requests = int(num)
        
        duration_components = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        duration = duration_components.get(period[0], 60)
        
        return (num_requests, duration)
    
    def allow_request(self, request: HttpRequest, view: APIView) -> bool:
        """Check request against dynamic rate limit."""
        self.rate = self.get_rate()
        num_requests, duration = self.parse_rate(self.rate)
        
        if num_requests is None:
            return True
        
        ident = self.get_ident(request)
        cache_key = f"throttle_dynamic_{ident}"
        
        # Get current request count
        history = cache.get(cache_key, [])
        now = self.now()
        
        # Filter to current window
        while history and history[-1] <= now - duration:
            history.pop()
        
        if len(history) >= num_requests:
            return False
        
        history.insert(0, now)
        cache.set(cache_key, history, duration)
        return True
    
    def wait(self) -> Optional[float]:
        """Calculate wait time until next request allowed."""
        num_requests, duration = self.parse_rate(self.rate)
        ident = self.get_ident()
        cache_key = f"throttle_dynamic_{ident}"
        history = cache.get(cache_key, [])
        
        if not history:
            return None
        
        now = self.now()
        window_start = now - duration
        
        # Find when window will have space
        if len(history) >= num_requests:
            oldest_in_window = history[-1]
            wait_time = oldest_in_window - window_start
            return max(wait_time, 1.0)
        
        return None


class RateLimitHeadersMiddleware:
    """Middleware to add rate limit headers to responses.
    
    Adds standard rate limit headers for client awareness:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Remaining requests in window
    - X-RateLimit-Reset: Unix timestamp when limit resets
    """
    
    def __init__(self, get_response: Callable):
        self.get_response = get_response
    
    def __call__(self, request: HttpRequest):
        """Process request and add rate limit headers."""
        response = self.get_response(request)
        
        # Add rate limit info from request if available
        rate_limit_info = getattr(request, "_rate_limit_info", None)
        if rate_limit_info:
            response["X-RateLimit-Limit"] = str(rate_limit_info.get("limit", ""))
            response["X-RateLimit-Remaining"] = str(rate_limit_info.get("remaining", ""))
            response["X-RateLimit-Reset"] = str(rate_limit_info.get("reset", ""))
        
        return response


def get_throttle_classes(throttle_type: str = "default") -> List[type]:
    """Get appropriate throttle classes based on throttle type.
    
    Args:
        throttle_type: Type of throttling to apply
            - "default": Standard user throttling
            - "strict": Strict throttling for sensitive endpoints
            - "admin": Admin bypass with standard throttling
            - "content": Content creation throttling
            - "export": Export operation throttling
            - "audit": Audit endpoint throttling
            - "anonymous": IP-based throttling only
            
    Returns:
        List of throttle classes to apply
    """
    throttle_configs: Dict[str, List[type]] = {
        "default": [
            BurstRateThrottle,
            SustainedRateThrottle,
        ],
        "strict": [
            BurstRateThrottle,
            SustainedRateThrottle,
            IPRateThrottle,
        ],
        "admin": [
            AdminBypassThrottle,
            BurstRateThrottle,
        ],
        "content": [
            ContentCreationThrottle,
            BurstRateThrottle,
        ],
        "export": [
            ExportThrottle,
        ],
        "audit": [
            AuditSensitiveThrottle,
        ],
        "anonymous": [
            IPRateThrottle,
        ],
        "webhook": [
            WebhookThrottle,
        ],
        "premium": [
            PremiumUserRateThrottle,
        ],
        "dynamic": [
            DynamicRateThrottle,
        ],
    }
    
    return throttle_configs.get(throttle_type, throttle_configs["default"])


def configure_rate_limit_settings() -> Dict[str, Any]:
    """Get complete rate limiting configuration for REST_FRAMEWORK settings.
    
    Returns configuration dictionary for use in settings.REST_FRAMEWORK.
    """
    return {
        "DEFAULT_THROTTLE_CLASSES": [
            "utils.throttling.BurstRateThrottle",
            "utils.throttling.SustainedRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {
            # User-based throttling
            "burst": "20/minute",
            "sustained": "1000/hour",
            "premium": "5000/hour",
            
            # IP-based throttling
            "ip": "100/hour",
            "anon": "100/hour",
            
            # Endpoint-specific throttling
            "content_creation": "10/minute",
            "export": "5/hour",
            "audit_sensitive": "30/minute",
            "webhook": "60/minute",
            
            # Dynamic throttling
            "dynamic": "100/minute",
        },
    }


class RateLimitInfo:
    """Information about current rate limit status.
    
    Used to populate rate limit headers and provide client feedback.
    """
    
    def __init__(
        self,
        limit: int,
        remaining: int,
        reset_timestamp: int,
        window: str,
    ):
        self.limit = limit
        self.remaining = remaining
        self.reset_timestamp = reset_timestamp
        self.window = window
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for response headers."""
        return {
            "limit": self.limit,
            "remaining": self.remaining,
            "reset": self.reset_timestamp,
            "window": self.window,
        }
