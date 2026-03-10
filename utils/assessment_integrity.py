"""Assessment integrity scoring helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class IntegrityEvent:
    learner_id: str
    exam_id: str
    severity: str
    incident_count: int
    proctor_flag: bool


@dataclass(frozen=True)
class IntegrityScore:
    learner_id: str
    score: float
    band: str
    flags: List[str]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_integrity(events: Iterable[IntegrityEvent], learner_id: str) -> IntegrityScore:
    rows = [item for item in events if item.learner_id == learner_id]
    if not rows:
        return IntegrityScore(learner_id, 100.0, "clean", [])

    incidents = sum(max(0, item.incident_count) for item in rows)
    severe = len([item for item in rows if item.severity in {"high", "critical"}])
    proctor_flags = len([item for item in rows if item.proctor_flag])

    score = _clamp(100.0 - incidents * 5.0 - severe * 15.0 - proctor_flags * 10.0)
    band = "clean"
    flags: List[str] = []

    if score < 85:
        band = "watch"
        flags.append("manual-review")
    if score < 65 or severe > 0:
        band = "risk"
        flags.append("hold-credential")

    return IntegrityScore(learner_id, round(score, 2), band, flags)


def integrity_summary(events: Iterable[IntegrityEvent]) -> Dict[str, int]:
    learners = sorted({item.learner_id for item in events})
    summary = {"clean": 0, "watch": 0, "risk": 0}
    for learner_id in learners:
        summary[evaluate_integrity(events, learner_id).band] += 1
    return summary


def flagged_learners(events: Iterable[IntegrityEvent]) -> List[str]:
    learners = sorted({item.learner_id for item in events})
    return [learner for learner in learners if evaluate_integrity(events, learner).band != "clean"]


def exam_hotspots(events: Iterable[IntegrityEvent]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for event in events:
        if event.severity in {"high", "critical"} or event.proctor_flag:
            counts[event.exam_id] = counts.get(event.exam_id, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def integrity_digest(events: Iterable[IntegrityEvent]) -> Dict[str, object]:
    return {
        "summary": integrity_summary(events),
        "flagged_learners": flagged_learners(events),
        "exam_hotspots": exam_hotspots(events),
    }


def proctor_flag_rate(events: Iterable[IntegrityEvent]) -> float:
    rows = list(events)
    if not rows:
        return 0.0
    flagged = len([row for row in rows if row.proctor_flag])
    return round((flagged / len(rows)) * 100.0, 2)
