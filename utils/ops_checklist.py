"""Operational checklist helpers for release runbooks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    description: str
    required: bool
    completed: bool


DEFAULT_CHECKLIST = [
    ChecklistItem(key="db-backup", description="Database backup completed", required=True, completed=False),
    ChecklistItem(key="cache-warmup", description="Cache warmup complete", required=False, completed=False),
    ChecklistItem(key="pager-on-call", description="On-call acknowledged", required=True, completed=False),
    ChecklistItem(key="rollout-plan", description="Rollout plan shared", required=True, completed=False),
]


def complete_items(items: Iterable[ChecklistItem], completed_keys: Iterable[str]) -> List[ChecklistItem]:
    completed = set(completed_keys)
    result: List[ChecklistItem] = []

    for item in items:
        result.append(
            ChecklistItem(
                key=item.key,
                description=item.description,
                required=item.required,
                completed=item.key in completed,
            )
        )

    return result


def checklist_summary(items: Iterable[ChecklistItem]) -> Dict[str, int]:
    required_total = 0
    required_completed = 0
    optional_total = 0
    optional_completed = 0

    for item in items:
        if item.required:
            required_total += 1
            if item.completed:
                required_completed += 1
        else:
            optional_total += 1
            if item.completed:
                optional_completed += 1

    return {
        "required_total": required_total,
        "required_completed": required_completed,
        "optional_total": optional_total,
        "optional_completed": optional_completed,
    }


def can_release(items: Iterable[ChecklistItem]) -> bool:
    for item in items:
        if item.required and not item.completed:
            return False
    return True


def incomplete_required_items(items: Iterable[ChecklistItem]) -> List[str]:
    return [item.key for item in items if item.required and not item.completed]
