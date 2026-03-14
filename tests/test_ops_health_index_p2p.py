from __future__ import annotations

from utils.ops_health_index import OpsWindow, derive_indicator, summarise_environment


def test_p2p_001_production_happy_path_yields_strong_scores() -> None:
    windows = [
        OpsWindow(
            window_id="2026-03-14T09",
            environment="production",
            total_requests=200_000,
            failed_requests=120,
            p95_latency_ms=320,
            error_budget_minutes=60,
            downtime_minutes=2,
            change_failure_count=0,
            deployment_count=15,
        ),
        OpsWindow(
            window_id="2026-03-14T10",
            environment="production",
            total_requests=210_000,
            failed_requests=140,
            p95_latency_ms=340,
            error_budget_minutes=60,
            downtime_minutes=0,
            change_failure_count=1,
            deployment_count=12,
        ),
    ]

    summaries = summarise_environment(windows)
    production = summaries["production"]

    assert production.environment == "production"
    assert production.window_count == len(windows)
    assert 80 <= production.average_score <= 100
    assert production.regression_detected is False


def test_p2p_002_sustained_degradation_triggers_regression_flag() -> None:
    baseline = OpsWindow(
        window_id="001",
        environment="prod",
        total_requests=100_000,
        failed_requests=80,
        p95_latency_ms=300,
        error_budget_minutes=60,
        downtime_minutes=1,
        change_failure_count=0,
        deployment_count=10,
    )
    degraded = OpsWindow(
        window_id="002",
        environment="prod",
        total_requests=baseline.total_requests,
        failed_requests=baseline.failed_requests * 5,
        p95_latency_ms=900,
        error_budget_minutes=60,
        downtime_minutes=25,
        change_failure_count=3,
        deployment_count=baseline.deployment_count,
    )

    summaries = summarise_environment([baseline, degraded])

    assert summaries["production"].regression_detected is True
    assert summaries["production"].worst_score < summaries["production"].best_score


def test_p2p_003_low_traffic_environments_are_still_accounted_for() -> None:
    prod = OpsWindow(
        window_id="p-low",
        environment="prod",
        total_requests=50,
        failed_requests=1,
        p95_latency_ms=410,
        error_budget_minutes=15,
        downtime_minutes=0,
        change_failure_count=0,
        deployment_count=1,
    )
    dev = OpsWindow(
        window_id="d-low",
        environment="dev",
        total_requests=0,
        failed_requests=0,
        p95_latency_ms=0,
        error_budget_minutes=0,
        downtime_minutes=0,
        change_failure_count=0,
        deployment_count=0,
    )

    summaries = summarise_environment([prod, dev])

    assert "production" in summaries
    assert "development" in summaries
    assert summaries["development"].average_score >= 70


def test_p2p_004_indicator_scores_move_together_for_multi_dimensional_regressions() -> None:
    healthy = OpsWindow(
        window_id="h1",
        environment="production",
        total_requests=150_000,
        failed_requests=90,
        p95_latency_ms=310,
        error_budget_minutes=60,
        downtime_minutes=1,
        change_failure_count=0,
        deployment_count=8,
    )
    noisy = OpsWindow(
        window_id="h2",
        environment="production",
        total_requests=healthy.total_requests,
        failed_requests=healthy.failed_requests * 4,
        p95_latency_ms=healthy.p95_latency_ms * 2,
        error_budget_minutes=healthy.error_budget_minutes,
        downtime_minutes=healthy.downtime_minutes + 20,
        change_failure_count=healthy.change_failure_count + 3,
        deployment_count=healthy.deployment_count,
    )

    healthy_indicator = derive_indicator(healthy)
    noisy_indicator = derive_indicator(noisy)

    assert noisy_indicator.availability_score < healthy_indicator.availability_score
    assert noisy_indicator.latency_score < healthy_indicator.latency_score
    assert noisy_indicator.stability_score < healthy_indicator.stability_score
    assert noisy_indicator.overall_score < healthy_indicator.overall_score

