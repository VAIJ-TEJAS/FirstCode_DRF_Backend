"""Aligned with FirstCode_React_Frontend sloForecasterFixtures.ts."""

from __future__ import annotations

from typing import Any, Dict


def base(svc_id: str) -> Dict[str, Any]:
    return {
        "serviceId": svc_id,
        "sloTargetAvailabilityPct": 99.9,
        "windowKind": "24h",
        "windowHours": 24,
        "goodEvents": 120_000,
        "badEvents": 40,
        "errorBudgetRemainingPct": 48,
    }


BATCH_HEALTHY = base("svc-api-healthy")

HOT_BURN_CHECKOUT: Dict[str, Any] = {
    **base("svc-checkout-hot"),
    "goodEvents": 50_000,
    "badEvents": 900,
    "errorBudgetRemainingPct": 7,
    "windowHours": 6,
    "windowKind": "6h",
}

LOW_BUDGET_PAYMENTS: Dict[str, Any] = {
    **base("svc-payments-low"),
    "errorBudgetRemainingPct": 5,
    "badEvents": 120,
    "goodEvents": 200_000,
}

SPARSE_EDGE: Dict[str, Any] = {
    **base("svc-edge-sparse"),
    "goodEvents": 12,
    "badEvents": 2,
    "errorBudgetRemainingPct": 40,
    "windowHours": 1,
    "windowKind": "1h",
}

MISCONFIGURED_SLO: Dict[str, Any] = {
    **base("svc-bad-slo"),
    "sloTargetAvailabilityPct": 100,
    "goodEvents": 1000,
    "badEvents": 0,
}
