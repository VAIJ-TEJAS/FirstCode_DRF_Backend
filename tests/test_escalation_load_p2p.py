import importlib.util
import pytest


MODULE_PATH = "utils.escalation_load"


def test_escalation_load_p2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("escalation load module not available")

    from utils.escalation_load import EscalationLoad, load_pressure

    pressure = load_pressure([
        EscalationLoad(owner="ops", open_cases=14, avg_age_hours=22),
        EscalationLoad(owner="support", open_cases=8, avg_age_hours=30),
    ])

    assert pressure["pressure"] == "medium"
