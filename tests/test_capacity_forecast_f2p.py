import importlib.util
import pytest


MODULE_PATH = "utils.capacity_forecast"


def test_capacity_forecast_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("capacity forecast module not available")

    from utils.capacity_forecast import CapacitySignal, forecast_capacity

    forecast = forecast_capacity([
        CapacitySignal(week="2026-W01", seats=200, utilization=0.92),
        CapacitySignal(week="2026-W02", seats=220, utilization=0.88),
    ])

    assert forecast["risk_band"] == "high"
    assert forecast["available_seats"] > 0
