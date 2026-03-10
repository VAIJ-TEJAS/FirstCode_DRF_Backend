import importlib.util
import pytest


MODULE_PATH = "utils.tax_nexus"


def test_tax_nexus_p2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("tax nexus module not available")

    from utils.tax_nexus import NexusSignal, evaluate_nexus

    summary = evaluate_nexus([
        NexusSignal(
            jurisdiction="CA",
            annual_revenue=600000,
            transactions=120,
            threshold_revenue=500000,
            threshold_transactions=100,
        )
    ])

    assert summary[0].nexus is True
    assert summary[0].risk_score >= 100 or summary[0].risk_score == 100
