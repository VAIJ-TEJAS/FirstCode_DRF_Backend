import importlib.util
import pytest


MODULE_PATH = "utils.collections_forecast"


def test_collections_forecast_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("collections forecast module not available")

    from utils.collections_forecast import CollectionsPoint, forecast_recovery, recovery_trend

    points = [
        CollectionsPoint(period="2026-01", recovered=12000, written_off=2000),
        CollectionsPoint(period="2026-02", recovered=15000, written_off=1000),
    ]

    forecast = forecast_recovery(points)

    assert forecast["recovered_total"] == 27000
    assert forecast["writeoff_total"] == 3000
    assert forecast["recovery_rate"] == 90.0
    assert recovery_trend(points) == "accelerating"
