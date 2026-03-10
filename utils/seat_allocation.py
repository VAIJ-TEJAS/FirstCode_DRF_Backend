"""Seat allocation helpers for enterprise cohorts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class SeatRequest:
    request_id: str
    cohort_id: str
    seats_requested: int
    priority: int


@dataclass(frozen=True)
class AllocationResult:
    cohort_id: str
    seats_allocated: int
    waitlisted: int


def allocate_seats(requests: Iterable[SeatRequest], capacity: int) -> Dict[str, AllocationResult]:
    rows = sorted(list(requests), key=lambda row: (-row.priority, row.request_id))
    remaining = max(0, capacity)
    result: Dict[str, AllocationResult] = {}

    for row in rows:
        allocation = min(max(0, row.seats_requested), remaining)
        remaining -= allocation
        waitlisted = max(0, row.seats_requested - allocation)
        result[row.cohort_id] = AllocationResult(row.cohort_id, allocation, waitlisted)

    return result


def allocation_summary(results: Dict[str, AllocationResult]) -> Dict[str, int]:
    allocated = sum(item.seats_allocated for item in results.values())
    waitlisted = sum(item.waitlisted for item in results.values())
    return {"allocated": allocated, "waitlisted": waitlisted}


def cohort_waitlist(results: Dict[str, AllocationResult]) -> List[str]:
    return [cohort_id for cohort_id, result in results.items() if result.waitlisted > 0]


def allocation_digest(results: Dict[str, AllocationResult]) -> Dict[str, object]:
    return {
        "summary": allocation_summary(results),
        "waitlisted_cohorts": cohort_waitlist(results),
    }


def priority_map(requests: Iterable[SeatRequest]) -> Dict[str, int]:
    return {row.request_id: row.priority for row in requests}
