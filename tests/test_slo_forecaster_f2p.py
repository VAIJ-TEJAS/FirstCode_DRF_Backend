from __future__ import annotations

from utils.slo_forecaster import (
    classify_risk_tier,
    compute_max_bad_share_pct,
    compute_metrics,
    compute_score_breakdown,
    evaluate_slo_forecast,
    parse_forecast_from_json,
    round_half_up,
    total_events,
)

from tests.slo_forecaster_fixtures import BATCH_HEALTHY


def test_f2p_sf_001_math_helpers() -> None:
    assert total_events(3, 7) == 10
    assert round_half_up(2.5) == 3
    assert abs(compute_max_bad_share_pct(99.9) - 0.1) < 1e-9


def test_f2p_sf_002_parse_json() -> None:
    inp = parse_forecast_from_json(BATCH_HEALTHY)
    assert inp.service_id == "svc-api-healthy"


def test_f2p_sf_003_evaluate_shape() -> None:
    r = evaluate_slo_forecast(parse_forecast_from_json(BATCH_HEALTHY), "2026-03-22T12:00:00.000Z")
    assert r.risk_tier in {"green", "yellow", "orange", "red"}
    assert len(r.recommended_actions) >= 1


def test_f2p_sf_004_risk_tier_boundaries() -> None:
    assert classify_risk_tier(90) == "green"
    assert classify_risk_tier(70) == "yellow"
    assert classify_risk_tier(50) == "orange"
    assert classify_risk_tier(20) == "red"


def test_f2p_sf_005_metrics_nonzero_traffic() -> None:
    inp = parse_forecast_from_json(BATCH_HEALTHY)
    m = compute_metrics(inp)
    assert m.total_events > 0
    s = compute_score_breakdown(inp, m)
    assert 0 <= s.overall <= 100
