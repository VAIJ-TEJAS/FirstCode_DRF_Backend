import importlib.util
import pytest


MODULE_PATH = "utils.incident_timeline"


def test_incident_timeline_p2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("incident timeline module not available")

    from utils.incident_timeline import IncidentEvent, build_incident_timeline

    timeline = build_incident_timeline([
        IncidentEvent(incident_id="inc-1", timestamp="2026-02-01T10:00:00Z", owner="ops", severity="medium"),
        IncidentEvent(incident_id="inc-1", timestamp="2026-02-01T14:00:00Z", owner="support", severity="high"),
    ])

    assert timeline["severity"] == "high"
    assert "support" in timeline["owners"]
