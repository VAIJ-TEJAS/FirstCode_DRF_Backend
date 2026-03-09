"""Compliance digest helpers for enterprise edtech release reporting."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class ComplianceControl:
    key: str
    framework: str
    required: bool
    passed: bool
    note: str


@dataclass(frozen=True)
class ComplianceDigest:
    passed: bool
    blockers: List[str]
    framework_counts: Dict[str, int]
    score: int


def build_compliance_digest(controls: Iterable[ComplianceControl]) -> ComplianceDigest:
    blockers: List[str] = []
    framework_counts: Dict[str, int] = {}

    total = 0
    passed = 0

    for control in controls:
        total += 1
        framework_counts[control.framework] = framework_counts.get(control.framework, 0) + 1

        if control.passed:
            passed += 1
        elif control.required:
            blockers.append(f"{control.key}: {control.note}")

    score = 100
    if total > 0:
        score = int(round((passed / total) * 100))

    return ComplianceDigest(
        passed=len(blockers) == 0,
        blockers=blockers,
        framework_counts=framework_counts,
        score=score,
    )


def digest_lines(digest: ComplianceDigest) -> List[str]:
    lines = [
        f"passed={digest.passed}",
        f"score={digest.score}",
    ]

    for framework, count in sorted(digest.framework_counts.items()):
        lines.append(f"framework={framework} controls={count}")

    for blocker in digest.blockers:
        lines.append(f"BLOCKER {blocker}")

    return lines
