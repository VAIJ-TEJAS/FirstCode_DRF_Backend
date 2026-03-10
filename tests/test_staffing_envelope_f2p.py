import importlib.util
import pytest


MODULE_PATH = "utils.staffing_envelope"


def test_staffing_envelope_f2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("staffing envelope module not available")

    from utils.staffing_envelope import StaffingSignal, staffing_envelope

    envelope = staffing_envelope(StaffingSignal(team="support", required_fte=12, available_fte=6))

    assert envelope["risk_band"] == "high"
