"""Scholarship allocation scoring and recommendation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ScholarshipCandidate:
    learner_id: str
    need_score: float
    merit_score: float
    attendance_score: float
    retention_risk_score: float


@dataclass(frozen=True)
class AllocationDecision:
    learner_id: str
    score: float
    band: str
    recommended_amount: int


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_candidate(row: ScholarshipCandidate, budget_unit: int = 1000) -> AllocationDecision:
    score = _clamp(
        row.need_score * 0.40
        + row.merit_score * 0.25
        + row.attendance_score * 0.15
        + (100.0 - row.retention_risk_score) * 0.20
    )

    band = "waitlist"
    amount = 0
    if score >= 85:
        band = "priority"
        amount = budget_unit * 4
    elif score >= 70:
        band = "recommended"
        amount = budget_unit * 2
    elif score >= 55:
        band = "partial"
        amount = budget_unit

    return AllocationDecision(row.learner_id, round(score, 2), band, amount)


def rank_candidates(rows: Iterable[ScholarshipCandidate]) -> List[AllocationDecision]:
    return sorted([evaluate_candidate(row) for row in rows], key=lambda item: item.score, reverse=True)


def budget_plan(rows: Iterable[ScholarshipCandidate], total_budget: int) -> Dict[str, object]:
    ranked = rank_candidates(rows)
    allocated = 0
    approved: List[AllocationDecision] = []

    for item in ranked:
        if allocated + item.recommended_amount > total_budget:
            continue
        if item.recommended_amount <= 0:
            continue
        approved.append(item)
        allocated += item.recommended_amount

    return {
        "approved_count": len(approved),
        "allocated": allocated,
        "remaining": max(0, total_budget - allocated),
        "approved": [item.learner_id for item in approved],
    }


def allocation_breakdown(rows: Iterable[ScholarshipCandidate]) -> Dict[str, int]:
    summary = {"priority": 0, "recommended": 0, "partial": 0, "waitlist": 0}
    for item in rank_candidates(rows):
        summary[item.band] += 1
    return summary


def fairness_check(rows: Iterable[ScholarshipCandidate]) -> Dict[str, float]:
    ranked = rank_candidates(rows)
    if not ranked:
        return {"top_score": 0.0, "bottom_score": 0.0, "spread": 0.0}

    top = ranked[0].score
    bottom = ranked[-1].score
    return {
        "top_score": top,
        "bottom_score": bottom,
        "spread": round(top - bottom, 2),
    }


def simulate_budget_scenarios(rows: Iterable[ScholarshipCandidate], budgets: Iterable[int]) -> Dict[int, Dict[str, object]]:
    candidates = list(rows)
    scenarios: Dict[int, Dict[str, object]] = {}
    for budget in sorted(list(budgets)):
        scenarios[budget] = {
            "plan": budget_plan(candidates, budget),
            "breakdown": allocation_breakdown(candidates),
            "fairness": fairness_check(candidates),
        }
    return scenarios
