from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class OpsWindow:
    """
    A coarse-grained window of operational signals for a given environment.

    The backend deliberately keeps this type fairly generic so it can be used
    both for production monitoring style checks and as a compact input for
    evaluator-style unit tests.
    """

    window_id: str
    environment: str
    total_requests: int
    failed_requests: int
    p95_latency_ms: int
    error_budget_minutes: int
    downtime_minutes: int
    change_failure_count: int
    deployment_count: int


@dataclass(frozen=True)
class OpsIndicator:
    """
    Derived indicator for a single window, normalised on a 0–100 scale.
    """

    window_id: str
    availability_score: int
    latency_score: int
    stability_score: int
    overall_score: int


@dataclass(frozen=True)
class OpsHealthSummary:
    """
    Aggregated view across several windows.
    """

    environment: str
    average_score: int
    worst_score: int
    best_score: int
    window_count: int
    regression_detected: bool


def _safe_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return max(0.0, min(1.0, numerator / denominator))


def classify_environment(raw: str | None) -> str:
    """
    Normalise environment labels used in observability systems.
    """

    if not raw:
        return "development"

    value = raw.strip().lower()

    if value in {"prod", "production", "live"}:
        return "production"
    if value in {"stage", "staging", "preprod"}:
        return "staging"
    if value in {"dev", "development", "local"}:
        return "development"

    return value


def score_availability(window: OpsWindow) -> int:
    """
    Convert uptime characteristics into a 0–100 availability score.
    """

    if window.total_requests <= 0:
        # With no traffic, treat availability as neutral but not perfect.
        base = 80
    else:
        failure_ratio = _safe_ratio(window.failed_requests, window.total_requests)
        # The closer to zero failures, the closer we get to 100.
        base = round((1.0 - failure_ratio) * 100)

    if window.error_budget_minutes <= 0:
        budget_penalty = 15
    else:
        budget_ratio = _safe_ratio(window.downtime_minutes, window.error_budget_minutes)
        if budget_ratio <= 0.25:
            budget_penalty = 0
        elif budget_ratio <= 0.5:
            budget_penalty = 5
        elif budget_ratio <= 0.75:
            budget_penalty = 10
        else:
            budget_penalty = 20

    return max(0, min(100, base - budget_penalty))


def score_latency(window: OpsWindow, budget_ms: int = 600) -> int:
    """
    Score latency against a soft p95 budget.
    """

    if window.p95_latency_ms <= 0:
        return 100

    ratio = window.p95_latency_ms / max(1, budget_ms)

    if ratio <= 0.5:
        return 100
    if ratio <= 1.0:
        # From 0.5× budget to 1× budget we linearly step down to 85.
        return max(85, round(100 - (ratio - 0.5) * 30))
    if ratio <= 2.0:
        # Between 1× and 2× budget we compress harder down to 60.
        return max(60, round(85 - (ratio - 1.0) * 50))

    # Very slow windows are heavily penalised.
    return max(10, round(60 - (ratio - 2.0) * 40))


def score_stability(window: OpsWindow) -> int:
    """
    Capture deployment stability using a very small set of inputs.
    """

    if window.deployment_count <= 0:
        return 100

    change_failure_rate = _safe_ratio(window.change_failure_count, window.deployment_count)

    if change_failure_rate == 0:
        return 100
    if change_failure_rate <= 0.15:
        return 90
    if change_failure_rate <= 0.3:
        return 75
    if change_failure_rate <= 0.5:
        return 60

    return 40


def derive_indicator(window: OpsWindow) -> OpsIndicator:
    """
    Produce a consolidated indicator for a single window.
    """

    availability = score_availability(window)
    latency = score_latency(window)
    stability = score_stability(window)

    overall = round((availability * 0.45) + (latency * 0.25) + (stability * 0.30))

    return OpsIndicator(
        window_id=window.window_id,
        availability_score=availability,
        latency_score=latency,
        stability_score=stability,
        overall_score=max(0, min(100, overall)),
    )


def summarise_environment(windows: Iterable[OpsWindow]) -> Dict[str, OpsHealthSummary]:
    """
    Build an environment-level view of operational health.
    """

    grouped: Dict[str, List[Tuple[OpsWindow, OpsIndicator]]] = {}

    for window in windows:
        env = classify_environment(window.environment)
        indicator = derive_indicator(window)
        grouped.setdefault(env, []).append((window, indicator))

    summaries: Dict[str, OpsHealthSummary] = {}

    for env, items in grouped.items():
        if not items:
            continue

        indicators = [indicator for _, indicator in items]
        scores = [indicator.overall_score for indicator in indicators]
        average_score = round(sum(scores) / len(scores))
        worst_score = min(scores)
        best_score = max(scores)

        regression_detected = False

        # Detect any monotonic downward movement of at least 15 points across
        # consecutive windows for the same environment. This is purposely simple
        # but robust enough for tests and day‑to‑day usage.
        sorted_items = sorted(items, key=lambda pair: pair[0].window_id)
        for index in range(1, len(sorted_items)):
            previous = sorted_items[index - 1][1].overall_score
            current = sorted_items[index][1].overall_score
            if previous - current >= 15:
                regression_detected = True
                break

        summaries[env] = OpsHealthSummary(
            environment=env,
            average_score=max(0, min(100, average_score)),
            worst_score=worst_score,
            best_score=best_score,
            window_count=len(items),
            regression_detected=regression_detected,
        )

    return summaries

