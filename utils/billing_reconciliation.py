from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class InvoiceLine:
    invoice_id: str
    amount: float
    paid: float


@dataclass(frozen=True)
class ReconciliationSummary:
    invoice_id: str
    balance: float
    status: str


def compute_invoice_balance(amount: float, paid: float) -> float:
    return round(max(amount - paid, 0.0), 2)


def reconcile_invoices(lines: Iterable[InvoiceLine]) -> List[ReconciliationSummary]:
    summaries: List[ReconciliationSummary] = []
    for line in lines:
        balance = compute_invoice_balance(line.amount, line.paid)
        status = "paid" if balance == 0 else "open" if balance > 0 else "credit"
        summaries.append(ReconciliationSummary(line.invoice_id, balance, status))
    return summaries


def reconciliation_report(lines: Iterable[InvoiceLine]) -> dict:
    summaries = reconcile_invoices(lines)
    outstanding = sum(item.balance for item in summaries)
    paid_count = sum(1 for item in summaries if item.status == "paid")
    return {
        "outstanding": round(outstanding, 2),
        "paid_count": paid_count,
        "open_count": len(summaries) - paid_count,
        "summaries": summaries,
    }
