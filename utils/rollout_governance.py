"""Rollout governance helpers for enterprise release orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class RolloutCheckpoint:
    key: str
    description: str
    required: bool
    status: str


@dataclass(frozen=True)
class RolloutGovernanceReport:
    approved: bool
    blockers: List[str]
    warnings: List[str]
    summary: Dict[str, int]


def _is_complete(status: str) -> bool:
    return status.strip().lower() in {"complete", "done", "passed", "ok"}


def _is_warning(status: str) -> bool:
    return status.strip().lower() in {"partial", "warning", "degraded"}


def evaluate_rollout_governance(checkpoints: Iterable[RolloutCheckpoint]) -> RolloutGovernanceReport:
    blockers: List[str] = []
    warnings: List[str] = []

    required_total = 0
    required_complete = 0
    optional_total = 0
    optional_complete = 0

    for checkpoint in checkpoints:
        if checkpoint.required:
            required_total += 1
            if _is_complete(checkpoint.status):
                required_complete += 1
            else:
                blockers.append(f"{checkpoint.key}: {checkpoint.description}")
        else:
            optional_total += 1
            if _is_complete(checkpoint.status):
                optional_complete += 1
            elif _is_warning(checkpoint.status):
                warnings.append(f"{checkpoint.key}: {checkpoint.description}")

    approved = len(blockers) == 0

    return RolloutGovernanceReport(
        approved=approved,
        blockers=blockers,
        warnings=warnings,
        summary={
            "required_total": required_total,
            "required_complete": required_complete,
            "optional_total": optional_total,
            "optional_complete": optional_complete,
        },
    )


def default_governance_checkpoints() -> List[RolloutCheckpoint]:
    return [
        RolloutCheckpoint(
            key="db-backup",
            description="Database backup validated",
            required=True,
            status="pending",
        ),
        RolloutCheckpoint(
            key="cache-warmup",
            description="Cache warmup complete",
            required=False,
            status="pending",
        ),
        RolloutCheckpoint(
            key="security-scan",
            description="Security scan has no blocking findings",
            required=True,
            status="pending",
        ),
        RolloutCheckpoint(
            key="support-briefed",
            description="Support team has rollout briefing",
            required=False,
            status="pending",
        ),
    ]


def to_lines(report: RolloutGovernanceReport) -> List[str]:
    lines: List[str] = []

    lines.append(f"approved={report.approved}")
    lines.append(f"required={report.summary['required_complete']}/{report.summary['required_total']}")
    lines.append(f"optional={report.summary['optional_complete']}/{report.summary['optional_total']}")

    for blocker in report.blockers:
        lines.append(f"BLOCKER {blocker}")

    for warning in report.warnings:
        lines.append(f"WARNING {warning}")

    return lines
