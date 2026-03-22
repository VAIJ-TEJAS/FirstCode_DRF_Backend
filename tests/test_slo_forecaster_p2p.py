from __future__ import annotations

from utils.slo_forecaster import evaluate_slo_forecast, parse_forecast_from_json

from tests.slo_forecaster_fixtures import (
    BATCH_HEALTHY,
    HOT_BURN_CHECKOUT,
    LOW_BUDGET_PAYMENTS,
    MISCONFIGURED_SLO,
    SPARSE_EDGE,
)


def test_p2p_sf_010_golden_risk_tiers() -> None:
    iso = "2026-03-22T12:00:00.000Z"
    assert evaluate_slo_forecast(parse_forecast_from_json(BATCH_HEALTHY), iso).risk_tier == "green"
    assert evaluate_slo_forecast(parse_forecast_from_json(HOT_BURN_CHECKOUT), iso).risk_tier in {"orange", "red"}
    assert evaluate_slo_forecast(parse_forecast_from_json(LOW_BUDGET_PAYMENTS), iso).risk_tier == "red"
    assert evaluate_slo_forecast(parse_forecast_from_json(SPARSE_EDGE), iso).risk_tier == "yellow"
    assert evaluate_slo_forecast(parse_forecast_from_json(MISCONFIGURED_SLO), iso).risk_tier == "red"


def test_p2p_sf_011_hot_burn_has_issue() -> None:
    r = evaluate_slo_forecast(parse_forecast_from_json(HOT_BURN_CHECKOUT), "2026-03-22T12:00:00.000Z")
    assert r.metrics.burn_multiple > 2
    assert any(i.code == "burn_hot" for i in r.issues)
