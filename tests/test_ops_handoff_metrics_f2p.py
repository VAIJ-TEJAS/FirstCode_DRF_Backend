import importlib.util
import pytest


MODULE_PATH = "utils.ops_handoff_metrics"


def test_ops_handoff_metrics_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("ops handoff metrics module not available")

    from utils.ops_handoff_metrics import HandoffMetric, handoff_metrics

    summary = handoff_metrics([
        HandoffMetric(owner="ops", handoffs=4, avg_delay_hours=2),
        HandoffMetric(owner="support", handoffs=6, avg_delay_hours=3),
    ])

    assert summary["handoffs"] == 10
    assert summary["avg_delay"] == 2.5
