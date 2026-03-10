"""Enterprise recovery playbooks for critical incidents."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class RecoveryStep:
    step_id: str
    service: str
    priority: int
    owner: str
    eta_minutes: int


@dataclass(frozen=True)
class RecoveryPlan:
    service: str
    total_steps: int
    critical_steps: int
    estimated_minutes: int


def build_plan(steps: Iterable[RecoveryStep], service: str) -> RecoveryPlan:
    rows = [row for row in steps if row.service == service]
    total = len(rows)
    critical = len([row for row in rows if row.priority >= 8])
    eta = sum(max(0, row.eta_minutes) for row in rows)
    return RecoveryPlan(service, total, critical, eta)


def owner_queue(steps: Iterable[RecoveryStep]) -> Dict[str, int]:
    queue: Dict[str, int] = {}
    for row in steps:
        queue[row.owner] = queue.get(row.owner, 0) + 1
    return queue


def priority_order(steps: Iterable[RecoveryStep]) -> List[str]:
    return [row.step_id for row in sorted(steps, key=lambda item: (-item.priority, item.step_id))]


def recovery_digest(steps: Iterable[RecoveryStep], service: str) -> Dict[str, object]:
    plan = build_plan(steps, service)
    return {
        "service": plan.service,
        "total_steps": plan.total_steps,
        "critical_steps": plan.critical_steps,
        "estimated_minutes": plan.estimated_minutes,
        "owner_queue": owner_queue(steps),
        "priority_order": priority_order(steps),
    }


def steps_by_service(steps: Iterable[RecoveryStep]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in steps:
        counts[row.service] = counts.get(row.service, 0) + 1
    return counts


def recovery_score(plan: RecoveryPlan) -> int:
    score = 100
    score -= plan.critical_steps * 8
    score -= int(plan.estimated_minutes / 30) * 5
    return max(0, score)


def escalation_needed(plan: RecoveryPlan) -> bool:
    return plan.critical_steps >= 2 or plan.estimated_minutes >= 240


def owner_load(steps: Iterable[RecoveryStep]) -> Dict[str, int]:
    load: Dict[str, int] = {}
    for row in steps:
        load[row.owner] = load.get(row.owner, 0) + row.eta_minutes
    return load


def digest_all(steps: Iterable[RecoveryStep]) -> Dict[str, object]:
    rows = list(steps)
    services = sorted({row.service for row in rows})
    plans = {service: build_plan(rows, service) for service in services}
    return {
        "services": services,
        "plans": {service: plan.__dict__ for service, plan in plans.items()},
        "owner_load": owner_load(rows),
    }
