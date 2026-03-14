from __future__ import annotations

from utils.ops_health_index import (
    OpsWindow,
    classify_environment,
    derive_indicator,
    score_availability,
    score_latency,
    score_stability,
    summarise_environment,
)


def test_f2p_001_environment_labels_are_normalised_consistently() -> None:
    assert classify_environment("prod") == "production"
    assert classify_environment("PRODUCTION") == "production"
    assert classify_environment("stage") == "staging"
    assert classify_environment("dev") == "development"
    assert classify_environment("") == "development"


def test_f2p_002_availability_handles_zero_traffic_reasonably() -> None:
    window = OpsWindow(
        window_id="w0",
        environment="prod",
        total_requests=0,
        failed_requests=0,
        p95_latency_ms=300,
        error_budget_minutes=60,
        downtime_minutes=0,
        change_failure_count=0,
        deployment_count=0,
    )

    score = score_availability(window)

    assert 70 <= score <= 90


def test_f2p_003_availability_penalises_budget_exhaustion() -> None:
    healthy = OpsWindow(
        window_id="w1",
        environment="prod",
        total_requests=100_000,
        failed_requests=100,
        p95_latency_ms=320,
        error_budget_minutes=60,
        downtime_minutes=5,
        change_failure_count=0,
        deployment_count=10,
    )
    exhausted = OpsWindow(
        window_id="w2",
        environment="prod",
        total_requests=healthy.total_requests,
        failed_requests=healthy.failed_requests,
        p95_latency_ms=healthy.p95_latency_ms,
        error_budget_minutes=60,
        downtime_minutes=55,
        change_failure_count=0,
        deployment_count=10,
    )

    healthy_score = score_availability(healthy)
    exhausted_score = score_availability(exhausted)

    assert healthy_score > exhausted_score
    assert exhausted_score <= healthy_score - 5


def test_f2p_004_latency_budget_reacts_to_slow_windows() -> None:
    fast = OpsWindow(
        window_id="wf",
        environment="prod",
        total_requests=50_000,
        failed_requests=25,
        p95_latency_ms=250,
        error_budget_minutes=30,
        downtime_minutes=0,
        change_failure_count=0,
        deployment_count=5,
    )
    borderline = OpsWindow(
        window_id="wb",
        environment="prod",
        total_requests=fast.total_requests,
        failed_requests=fast.failed_requests,
        p95_latency_ms=600,
        error_budget_minutes=30,
        downtime_minutes=0,
        change_failure_count=0,
        deployment_count=5,
    )
    slow = OpsWindow(
        window_id="ws",
        environment="prod",
        total_requests=fast.total_requests,
        failed_requests=fast.failed_requests,
        p95_latency_ms=1400,
        error_budget_minutes=30,
        downtime_minutes=0,
        change_failure_count=0,
        deployment_count=5,
    )

    fast_score = score_latency(fast)
    borderline_score = score_latency(borderline)
    slow_score = score_latency(slow)

    assert fast_score >= borderline_score >= slow_score
    assert slow_score < 80


def test_f2p_005_stability_tracks_change_failure_rate() -> None:
    stable = OpsWindow(
        window_id="s1",
        environment="prod",
        total_requests=10_000,
        failed_requests=50,
        p95_latency_ms=400,
        error_budget_minutes=45,
        downtime_minutes=2,
        change_failure_count=0,
        deployment_count=20,
    )
    spiky = OpsWindow(
        window_id="s2",
        environment="prod",
        total_requests=stable.total_requests,
        failed_requests=stable.failed_requests,
        p95_latency_ms=stable.p95_latency_ms,
        error_budget_minutes=stable.error_budget_minutes,
        downtime_minutes=stable.downtime_minutes,
        change_failure_count=6,
        deployment_count=12,
    )

    stable_score = score_stability(stable)
    spiky_score = score_stability(spiky)

    assert stable_score > spiky_score
    assert spiky_score <= 75


def test_f2p_006_indicator_combines_component_scores_reasonably() -> None:
    window = OpsWindow(
        window_id="combo",
        environment="prod",
        total_requests=120_000,
        failed_requests=900,
        p95_latency_ms=850,
        error_budget_minutes=60,
        downtime_minutes=20,
        change_failure_count=2,
        deployment_count=8,
    )

    indicator = derive_indicator(window)

    assert 0 <= indicator.availability_score <= 100
    assert 0 <= indicator.latency_score <= 100
    assert 0 <= indicator.stability_score <= 100
    assert 0 <= indicator.overall_score <= 100
    assert indicator.window_id == window.window_id


def test_f2p_007_summary_flags_regressions_across_ordered_windows() -> None:
    base = OpsWindow(
        window_id="0001",
        environment="prod",
        total_requests=100_000,
        failed_requests=100,
        p95_latency_ms=400,
        error_budget_minutes=60,
        downtime_minutes=1,
        change_failure_count=0,
        deployment_count=12,
    )
    regressed = OpsWindow(
        window_id="0002",
        environment="prod",
        total_requests=base.total_requests,
        failed_requests=base.failed_requests * 6,
        p95_latency_ms=base.p95_latency_ms * 2,
        error_budget_minutes=base.error_budget_minutes,
        downtime_minutes=base.downtime_minutes + 25,
        change_failure_count=base.change_failure_count + 4,
        deployment_count=base.deployment_count,
    )

    summaries = summarise_environment([base, regressed])
    production = summaries["production"]

    assert production.window_count == 2
    assert production.best_score >= production.worst_score
    assert production.regression_detected is True


def test_f2p_008_summary_handles_multiple_environments_independently() -> None:
    prod_window = OpsWindow(
        window_id="p1",
        environment="prod",
        total_requests=50_000,
        failed_requests=10,
        p95_latency_ms=350,
        error_budget_minutes=40,
        downtime_minutes=0,
        change_failure_count=0,
        deployment_count=6,
    )
    stage_window = OpsWindow(
        window_id="s1",
        environment="stage",
        total_requests=5_000,
        failed_requests=50,
        p95_latency_ms=900,
        error_budget_minutes=30,
        downtime_minutes=12,
        change_failure_count=1,
        deployment_count=4,
    )

    summaries = summarise_environment([prod_window, stage_window])

    assert "production" in summaries
    assert "staging" in summaries
    assert summaries["production"].average_score >= summaries["staging"].average_score

