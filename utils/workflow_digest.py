"""Workflow digest composition for enterprise reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from utils.grade_reconciliation import ReconciliationResult
from utils.proctoring_risk import ProctoringRiskReport


@dataclass(frozen=True)
class WorkflowDigest:
    release_id: str
    metrics: Dict[str, int]
    status: str


def compose_workflow_digest(
    release_id: str,
    risk_reports: Iterable[ProctoringRiskReport],
    reconciliations: Iterable[ReconciliationResult],
) -> WorkflowDigest:
    risk_reports = list(risk_reports)
    reconciliations = list(reconciliations)

    critical_risk = sum(1 for report in risk_reports if report.level == "critical")
    high_risk = sum(1 for report in risk_reports if report.level == "high")
    review_required = sum(1 for item in reconciliations if item.requires_review)

    status = "healthy"
    if critical_risk > 0:
        status = "blocked"
    elif high_risk > 0 or review_required > 0:
        status = "watch"

    return WorkflowDigest(
        release_id=release_id,
        metrics={
            "critical_risk": critical_risk,
            "high_risk": high_risk,
            "review_required": review_required,
            "reconciliation_count": len(reconciliations),
        },
        status=status,
    )


def digest_to_dict(digest: WorkflowDigest) -> Dict[str, object]:
    return {
        "release_id": digest.release_id,
        "status": digest.status,
        "metrics": dict(digest.metrics),
    }
