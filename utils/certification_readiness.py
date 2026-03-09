from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class CertificationModule:
    module_id: str
    required: bool
    weight: int


@dataclass(frozen=True)
class CertificationTrack:
    track_id: str
    passing_score: float
    modules: List[CertificationModule]


@dataclass(frozen=True)
class CertificationDecision:
    learner_id: str
    track_id: str
    status: str
    weighted_score: float
    completion_rate: float
    missing_required_modules: List[str]


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def evaluate_track(
    learner_id: str,
    track: CertificationTrack,
    module_scores: Dict[str, float],
) -> CertificationDecision:
    total_weight = 0
    weighted_sum = 0.0
    completed = 0
    missing_required: List[str] = []

    for module in track.modules:
        total_weight += module.weight
        if module.module_id in module_scores:
            completed += 1
            weighted_sum += _clamp_score(module_scores[module.module_id]) * module.weight
        elif module.required:
            missing_required.append(module.module_id)

    completion_rate = 0.0
    if track.modules:
        completion_rate = round((completed / len(track.modules)) * 100.0, 2)

    weighted_score = 0.0
    if total_weight > 0:
        weighted_score = round(weighted_sum / total_weight, 2)

    status = "not_started"
    if completion_rate > 0:
        status = "in_progress"
    if completion_rate == 100.0 and not missing_required and weighted_score >= track.passing_score:
        status = "eligible"
    elif completion_rate >= 50.0 and weighted_score < (track.passing_score - 10.0):
        status = "at_risk"

    return CertificationDecision(
        learner_id=learner_id,
        track_id=track.track_id,
        status=status,
        weighted_score=weighted_score,
        completion_rate=completion_rate,
        missing_required_modules=missing_required,
    )


def recommended_modules(track: CertificationTrack, module_scores: Dict[str, float], limit: int = 3) -> List[str]:
    pending = [m for m in track.modules if m.module_id not in module_scores]
    pending.sort(key=lambda item: (0 if item.required else 1, -item.weight, item.module_id))
    return [module.module_id for module in pending[: max(0, limit)]]
