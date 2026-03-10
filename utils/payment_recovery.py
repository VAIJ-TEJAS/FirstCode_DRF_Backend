from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class PaymentAttempt:
    invoice_id: str
    amount: float
    method: str
    success: bool


@dataclass(frozen=True)
class RecoveryPlan:
    invoice_id: str
    outstanding: float
    next_action: str
    retries: int


def build_recovery_plan(attempts: Iterable[PaymentAttempt]) -> List[RecoveryPlan]:
    plans: List[RecoveryPlan] = []
    grouped: dict[str, list[PaymentAttempt]] = {}
    for attempt in attempts:
        grouped.setdefault(attempt.invoice_id, []).append(attempt)

    for invoice_id, entries in grouped.items():
        last = entries[-1]
        success_count = sum(1 for entry in entries if entry.success)
        retries = len(entries) - success_count
        outstanding = round(sum(entry.amount for entry in entries if not entry.success), 2)
        next_action = "notify" if retries >= 2 else "retry"
        if last.success:
            next_action = "close"
            outstanding = 0.0
        plans.append(RecoveryPlan(invoice_id, outstanding, next_action, retries))
    return plans


def recovery_summary(attempts: Iterable[PaymentAttempt]) -> dict:
    plans = build_recovery_plan(attempts)
    total_outstanding = sum(plan.outstanding for plan in plans)
    return {
        "total_outstanding": round(total_outstanding, 2),
        "active_recoveries": sum(1 for plan in plans if plan.next_action != "close"),
        "plans": plans,
    }
