from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class ProbeResult:
    name: str
    status: str
    details: str


def aggregate_runtime_status(results: Iterable[ProbeResult]) -> str:
    statuses = [result.status for result in results]

    if any(status == "down" for status in statuses):
        return "down"
    if any(status == "degraded" for status in statuses):
        return "degraded"
    return "up"


def score_readiness(results: Iterable[ProbeResult]) -> int:
    weights = {"up": 100, "degraded": 60, "down": 0}
    values = [weights.get(result.status, 0) for result in results]
    if not values:
        return 0
    return round(sum(values) / len(values))


def classify_latency(latency_ms: float) -> str:
    if latency_ms >= 500:
        return "down"
    if latency_ms >= 120:
        return "degraded"
    return "up"


def classify_disk_capacity(free_percent: float) -> str:
    if free_percent <= 8:
        return "down"
    if free_percent <= 15:
        return "degraded"
    return "up"


def test_f2p_009_aggregate_runtime_status_returns_down_if_any_probe_is_down() -> None:
    status = aggregate_runtime_status(
        [
            ProbeResult(name="database", status="up", details="ok"),
            ProbeResult(name="cache", status="degraded", details="slow"),
            ProbeResult(name="disk", status="down", details="space low"),
        ]
    )

    assert status == "down"


def test_f2p_010_aggregate_runtime_status_returns_degraded_without_down() -> None:
    status = aggregate_runtime_status(
        [
            ProbeResult(name="database", status="up", details="ok"),
            ProbeResult(name="cache", status="degraded", details="slow"),
        ]
    )

    assert status == "degraded"


def test_f2p_011_aggregate_runtime_status_returns_up_when_all_up() -> None:
    status = aggregate_runtime_status(
        [
            ProbeResult(name="database", status="up", details="ok"),
            ProbeResult(name="cache", status="up", details="ok"),
            ProbeResult(name="disk", status="up", details="ok"),
        ]
    )

    assert status == "up"


def test_f2p_012_score_readiness_computes_weighted_average() -> None:
    score = score_readiness(
        [
            ProbeResult(name="database", status="up", details="ok"),
            ProbeResult(name="cache", status="degraded", details="slow"),
            ProbeResult(name="disk", status="up", details="ok"),
            ProbeResult(name="clock", status="down", details="skew"),
        ]
    )

    assert score == 65


def test_f2p_013_score_readiness_zero_for_empty_probe_list() -> None:
    assert score_readiness([]) == 0


def test_f2p_014_classify_latency_thresholds() -> None:
    assert classify_latency(30) == "up"
    assert classify_latency(180) == "degraded"
    assert classify_latency(800) == "down"


def test_f2p_015_classify_disk_capacity_thresholds() -> None:
    assert classify_disk_capacity(42) == "up"
    assert classify_disk_capacity(12) == "degraded"
    assert classify_disk_capacity(5) == "down"


def test_f2p_016_combined_flow_score_and_status_for_ci_gate() -> None:
    probes = [
        ProbeResult(name="database", status=classify_latency(40), details="query ok"),
        ProbeResult(name="cache", status=classify_latency(140), details="cache slow"),
        ProbeResult(name="disk", status=classify_disk_capacity(19), details="disk healthy"),
    ]

    status = aggregate_runtime_status(probes)
    score = score_readiness(probes)

    assert status == "degraded"
    assert score == 87
