"""Enterprise incident playbook orchestrator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class PlaybookStep:
    step_id: str
    label: str
    owner: str
    severity: str
    duration_minutes: int


@dataclass(frozen=True)
class PlaybookSummary:
    total_steps: int
    critical_steps: int
    estimated_minutes: int


def summarize_playbook(steps: Iterable[PlaybookStep]) -> PlaybookSummary:
    rows = list(steps)
    critical = len([row for row in rows if row.severity == "critical"])
    minutes = sum(max(0, row.duration_minutes) for row in rows)
    return PlaybookSummary(len(rows), critical, minutes)


def owner_steps(steps: Iterable[PlaybookStep]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in steps:
        counts[row.owner] = counts.get(row.owner, 0) + 1
    return counts


def severity_mix(steps: Iterable[PlaybookStep]) -> Dict[str, int]:
    mix: Dict[str, int] = {}
    for row in steps:
        mix[row.severity] = mix.get(row.severity, 0) + 1
    return mix


def playbook_digest(steps: Iterable[PlaybookStep]) -> Dict[str, object]:
    summary = summarize_playbook(steps)
    return {
        "summary": summary.__dict__,
        "owner_steps": owner_steps(steps),
        "severity_mix": severity_mix(steps),
    }


def critical_step_ids(steps: Iterable[PlaybookStep]) -> List[str]:
    return [row.step_id for row in steps if row.severity == "critical"]
