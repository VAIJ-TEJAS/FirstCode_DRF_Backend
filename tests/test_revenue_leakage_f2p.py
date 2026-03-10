import importlib.util
import pytest


MODULE_PATH = "utils.revenue_leakage"


def test_revenue_leakage_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("revenue leakage module not available")

    from utils.revenue_leakage import RevenueSignal, aggregate_leakage

    summary = aggregate_leakage([
        RevenueSignal(expected=100000, actual=92000),
        RevenueSignal(expected=20000, actual=18000),
    ])

    assert summary["expected_total"] == 120000
    assert summary["actual_total"] == 110000
    assert summary["leakage_rate"] == 8.33
