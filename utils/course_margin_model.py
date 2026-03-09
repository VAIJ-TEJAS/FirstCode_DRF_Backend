"""Course margin model for enterprise finance operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CourseFinanceRow:
    course_id: str
    revenue: float
    content_cost: float
    mentor_cost: float
    support_cost: float
    infra_cost: float


@dataclass(frozen=True)
class CourseMargin:
    course_id: str
    gross_margin: float
    margin_percent: float
    tier: str


def evaluate_margin(row: CourseFinanceRow) -> CourseMargin:
    total_cost = max(0.0, row.content_cost + row.mentor_cost + row.support_cost + row.infra_cost)
    gross = round(max(0.0, row.revenue) - total_cost, 2)
    margin_percent = round((gross / max(1.0, row.revenue)) * 100.0, 2)

    tier = "healthy"
    if margin_percent < 30:
        tier = "watch"
    if margin_percent < 15:
        tier = "critical"

    return CourseMargin(course_id=row.course_id, gross_margin=gross, margin_percent=margin_percent, tier=tier)


def portfolio_margin(rows: Iterable[CourseFinanceRow]) -> Dict[str, float]:
    margins = [evaluate_margin(row) for row in rows]
    if not margins:
        return {"average_margin_percent": 0.0, "critical_courses": 0.0}

    avg = round(sum(item.margin_percent for item in margins) / len(margins), 2)
    critical = float(len([item for item in margins if item.tier == "critical"]))
    return {"average_margin_percent": avg, "critical_courses": critical}


def tier_counts(rows: Iterable[CourseFinanceRow]) -> Dict[str, int]:
    summary = {"healthy": 0, "watch": 0, "critical": 0}
    for row in rows:
        summary[evaluate_margin(row).tier] += 1
    return summary


def margin_rankings(rows: Iterable[CourseFinanceRow]) -> List[CourseMargin]:
    return sorted([evaluate_margin(row) for row in rows], key=lambda row: row.margin_percent, reverse=True)


def margin_digest(rows: Iterable[CourseFinanceRow]) -> Dict[str, object]:
    ranked = margin_rankings(rows)
    if not ranked:
        return {
            "average_margin_percent": 0.0,
            "top_course": None,
            "bottom_course": None,
            "tier_counts": {"healthy": 0, "watch": 0, "critical": 0},
        }

    avg_margin = round(sum(item.margin_percent for item in ranked) / len(ranked), 2)
    return {
        "average_margin_percent": avg_margin,
        "top_course": ranked[0].course_id,
        "bottom_course": ranked[-1].course_id,
        "tier_counts": tier_counts(
            [
                CourseFinanceRow(
                    course_id=item.course_id,
                    revenue=100.0,
                    content_cost=max(0.0, 100.0 - item.gross_margin),
                    mentor_cost=0.0,
                    support_cost=0.0,
                    infra_cost=0.0,
                )
                for item in ranked
            ]
        ),
    }


def stress_test(rows: Iterable[CourseFinanceRow], revenue_drop_percent: float) -> Dict[str, object]:
    adjusted: List[CourseFinanceRow] = []
    drop_factor = max(0.0, min(1.0, revenue_drop_percent / 100.0))
    for row in rows:
        adjusted.append(
            CourseFinanceRow(
                course_id=row.course_id,
                revenue=round(row.revenue * (1.0 - drop_factor), 2),
                content_cost=row.content_cost,
                mentor_cost=row.mentor_cost,
                support_cost=row.support_cost,
                infra_cost=row.infra_cost,
            )
        )
    return {
        "drop_percent": revenue_drop_percent,
        "portfolio_margin": portfolio_margin(adjusted),
        "tier_counts": tier_counts(adjusted),
    }
