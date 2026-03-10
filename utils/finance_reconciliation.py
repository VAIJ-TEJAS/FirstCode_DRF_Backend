"""Finance reconciliation utilities for enterprise billing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class LedgerEntry:
    entry_id: str
    account_id: str
    amount: float
    category: str
    reconciled: bool


@dataclass(frozen=True)
class ReconciliationSummary:
    total_entries: int
    reconciled_count: int
    outstanding_amount: float
    category_totals: Dict[str, float]


def reconcile(entries: Iterable[LedgerEntry]) -> ReconciliationSummary:
    rows = list(entries)
    total_entries = len(rows)
    reconciled_count = len([row for row in rows if row.reconciled])
    category_totals: Dict[str, float] = {}
    outstanding = 0.0

    for row in rows:
        category_totals[row.category] = category_totals.get(row.category, 0.0) + max(0.0, row.amount)
        if not row.reconciled:
            outstanding += max(0.0, row.amount)

    return ReconciliationSummary(
        total_entries=total_entries,
        reconciled_count=reconciled_count,
        outstanding_amount=round(outstanding, 2),
        category_totals={k: round(v, 2) for k, v in category_totals.items()},
    )


def unreconciled_accounts(entries: Iterable[LedgerEntry]) -> List[str]:
    accounts: Dict[str, float] = {}
    for row in entries:
        if not row.reconciled:
            accounts[row.account_id] = accounts.get(row.account_id, 0.0) + max(0.0, row.amount)
    return [item[0] for item in sorted(accounts.items(), key=lambda item: (-item[1], item[0]))]


def category_rankings(entries: Iterable[LedgerEntry]) -> List[str]:
    summary = reconcile(entries).category_totals
    return [key for key, _ in sorted(summary.items(), key=lambda item: (-item[1], item[0]))]


def anomaly_flags(entries: Iterable[LedgerEntry], threshold: float = 10000.0) -> List[str]:
    flags = []
    for row in entries:
        if not row.reconciled and row.amount >= threshold:
            flags.append(row.entry_id)
    return flags


def reconciliation_digest(entries: Iterable[LedgerEntry]) -> Dict[str, object]:
    summary = reconcile(entries)
    return {
        "total_entries": summary.total_entries,
        "reconciled_count": summary.reconciled_count,
        "outstanding_amount": summary.outstanding_amount,
        "category_totals": summary.category_totals,
        "unreconciled_accounts": unreconciled_accounts(entries),
        "category_rankings": category_rankings(entries),
        "anomaly_flags": anomaly_flags(entries),
    }
