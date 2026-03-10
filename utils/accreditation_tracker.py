"""Accreditation tracker for enterprise compliance workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class AccreditationItem:
    item_id: str
    standard: str
    status: str
    owner: str
    evidence_count: int
    due_at_iso: str


@dataclass(frozen=True)
class AccreditationSummary:
    standard: str
    completion_percent: float
    overdue_count: int
    pending_items: int
    health: str


def _percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def summarize_standard(items: Iterable[AccreditationItem], standard: str) -> AccreditationSummary:
    rows = [item for item in items if item.standard == standard]
    if not rows:
        return AccreditationSummary(standard, 100.0, 0, 0, "healthy")

    completed = len([item for item in rows if item.status == "met"])
    pending = len([item for item in rows if item.status != "met"])
    overdue = len([item for item in rows if item.status == "overdue"])

    completion_percent = _percent(completed, len(rows))
    health = "healthy"
    if pending > 0:
        health = "watch"
    if overdue > 0:
        health = "critical"

    return AccreditationSummary(standard, completion_percent, overdue, pending, health)


def owner_backlog(items: Iterable[AccreditationItem]) -> Dict[str, int]:
    backlog: Dict[str, int] = {}
    for item in items:
        if item.status != "met":
            backlog[item.owner] = backlog.get(item.owner, 0) + 1
    return backlog


def evidence_gap(items: Iterable[AccreditationItem]) -> List[str]:
    return [item.item_id for item in items if item.evidence_count <= 0]


def standard_breakdown(items: Iterable[AccreditationItem]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for item in items:
        counts[item.standard] = counts.get(item.standard, 0) + 1
    return counts


def overdue_items(items: Iterable[AccreditationItem]) -> List[str]:
    return [item.item_id for item in items if item.status == "overdue"]


def accreditation_digest(items: Iterable[AccreditationItem]) -> Dict[str, object]:
    rows = list(items)
    standards = sorted({item.standard for item in rows})
    return {
        "standards": standards,
        "standard_breakdown": standard_breakdown(rows),
        "overdue_items": overdue_items(rows),
        "evidence_gap": evidence_gap(rows),
        "summaries": {standard: summarize_standard(rows, standard).__dict__ for standard in standards},
    }


def owner_matrix(items: Iterable[AccreditationItem]) -> Dict[str, Dict[str, int]]:
    matrix: Dict[str, Dict[str, int]] = {}
    for item in items:
        matrix.setdefault(item.owner, {"met": 0, "pending": 0, "overdue": 0})
        if item.status == "met":
            matrix[item.owner]["met"] += 1
        elif item.status == "overdue":
            matrix[item.owner]["overdue"] += 1
        else:
            matrix[item.owner]["pending"] += 1
    return matrix


def pending_by_owner(items: Iterable[AccreditationItem]) -> Dict[str, int]:
    return {owner: values["pending"] for owner, values in owner_matrix(items).items()}


def standard_status_map(items: Iterable[AccreditationItem]) -> Dict[str, str]:
    standards = sorted({item.standard for item in items})
    return {standard: summarize_standard(items, standard).health for standard in standards}
