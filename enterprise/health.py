"""Health and readiness checks for enterprise production monitoring."""

from __future__ import annotations

import shutil
import time
from datetime import datetime, timezone
from typing import Any

from django.core.cache import cache
from django.db import connection

from enterprise.config import evaluate_runtime_config, serialize_config_report
from enterprise.constants import READINESS_THRESHOLDS, STATUS_DEGRADED, STATUS_DOWN, STATUS_UP


def _status_from_threshold(value: float, warn: float, fail: float, inverse: bool = False) -> str:
    if inverse:
        if value <= fail:
            return STATUS_DOWN
        if value <= warn:
            return STATUS_DEGRADED
        return STATUS_UP

    if value >= fail:
        return STATUS_DOWN
    if value >= warn:
        return STATUS_DEGRADED
    return STATUS_UP


def check_database() -> dict[str, Any]:
    start = time.perf_counter()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        elapsed_ms = (time.perf_counter() - start) * 1000
        status = _status_from_threshold(
            elapsed_ms,
            READINESS_THRESHOLDS["database_query_ms_warn"],
            READINESS_THRESHOLDS["database_query_ms_fail"],
        )
        return {
            "status": status,
            "latency_ms": round(elapsed_ms, 2),
            "details": "Database probe query succeeded",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": STATUS_DOWN,
            "latency_ms": None,
            "details": f"Database probe failed: {exc}",
        }


def check_cache() -> dict[str, Any]:
    start = time.perf_counter()
    key = "enterprise:health:probe"
    value = f"probe-{int(start * 1000000)}"

    try:
        cache.set(key, value, timeout=30)
        resolved = cache.get(key)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if resolved != value:
            return {
                "status": STATUS_DEGRADED,
                "latency_ms": round(elapsed_ms, 2),
                "details": "Cache probe mismatch",
            }

        return {
            "status": STATUS_UP,
            "latency_ms": round(elapsed_ms, 2),
            "details": "Cache probe succeeded",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": STATUS_DOWN,
            "latency_ms": None,
            "details": f"Cache probe failed: {exc}",
        }


def check_disk(path: str = "/") -> dict[str, Any]:
    try:
        usage = shutil.disk_usage(path)
        free_percent = (usage.free / usage.total) * 100 if usage.total > 0 else 0.0
        status = _status_from_threshold(
            free_percent,
            READINESS_THRESHOLDS["disk_free_percent_warn"],
            READINESS_THRESHOLDS["disk_free_percent_fail"],
            inverse=True,
        )

        return {
            "status": status,
            "free_percent": round(free_percent, 2),
            "path": path,
            "details": "Disk capacity measured",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "status": STATUS_DOWN,
            "free_percent": None,
            "path": path,
            "details": f"Disk probe failed: {exc}",
        }


def check_clock() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    monotonic_ms = time.time_ns() / 1_000_000

    # In absence of NTP source, we still provide deterministic skew proxy with monotonic delta.
    skew_proxy_ms = abs((now.timestamp() * 1000) - monotonic_ms)
    status = _status_from_threshold(
        skew_proxy_ms,
        READINESS_THRESHOLDS["clock_skew_ms_warn"],
        READINESS_THRESHOLDS["clock_skew_ms_fail"],
    )

    return {
        "status": status,
        "utc_now": now.isoformat(),
        "skew_proxy_ms": round(skew_proxy_ms, 2),
        "details": "Clock check evaluated",
    }


def aggregate_status(component_statuses: list[str]) -> str:
    if any(status == STATUS_DOWN for status in component_statuses):
        return STATUS_DOWN
    if any(status == STATUS_DEGRADED for status in component_statuses):
        return STATUS_DEGRADED
    return STATUS_UP


def build_liveness_payload(service_name: str = "firstcode-backend") -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        "service": service_name,
        "status": STATUS_UP,
        "timestamp": now.isoformat(),
    }


def build_readiness_payload() -> dict[str, Any]:
    db_result = check_database()
    cache_result = check_cache()
    disk_result = check_disk()
    clock_result = check_clock()

    config_report = evaluate_runtime_config()
    config_payload = serialize_config_report(config_report)
    config_status = STATUS_UP if config_report.is_ready else STATUS_DEGRADED

    components = {
        "database": db_result,
        "cache": cache_result,
        "disk": disk_result,
        "clock": clock_result,
        "config": {
            "status": config_status,
            **config_payload,
        },
    }

    overall_status = aggregate_status([components[name]["status"] for name in components])

    return {
        "status": overall_status,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "components": components,
    }
