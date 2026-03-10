"""Policy simulation helpers for enterprise governance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class PolicyScenario:
    scenario_id: str
    warnings: int
    errors: int
    change_size: int
    requires_review: bool


@dataclass(frozen=True)
class PolicyOutcome:
    scenario_id: str
    risk: str
    approved: bool
    blockers: List[str]


def evaluate_scenario(scenario: PolicyScenario) -> PolicyOutcome:
    blockers: List[str] = []
    if scenario.errors > 0:
        blockers.append("errors-present")
    if scenario.requires_review:
        blockers.append("review-required")

    risk = "low"
    if scenario.warnings >= 3 or scenario.change_size > 1200:
        risk = "high"
    elif scenario.warnings >= 1 or scenario.change_size > 800:
        risk = "medium"

    approved = len(blockers) == 0
    return PolicyOutcome(scenario.scenario_id, risk, approved, blockers)


def scenario_matrix(scenarios: Iterable[PolicyScenario]) -> Dict[str, PolicyOutcome]:
    return {scenario.scenario_id: evaluate_scenario(scenario) for scenario in scenarios}


def risk_distribution(scenarios: Iterable[PolicyScenario]) -> Dict[str, int]:
    summary = {"low": 0, "medium": 0, "high": 0}
    for scenario in scenarios:
        summary[evaluate_scenario(scenario).risk] += 1
    return summary


def approval_rate(scenarios: Iterable[PolicyScenario]) -> float:
    rows = list(scenarios)
    if not rows:
        return 0.0
    approved = len([row for row in rows if evaluate_scenario(row).approved])
    return round((approved / len(rows)) * 100.0, 2)


def scenario_report(scenarios: Iterable[PolicyScenario]) -> Dict[str, object]:
    return {
        "count": len(list(scenarios)),
        "risk_distribution": risk_distribution(scenarios),
        "approval_rate": approval_rate(scenarios),
    }
