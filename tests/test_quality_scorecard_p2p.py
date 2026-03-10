import importlib.util
import pytest


MODULE_PATH = "utils.quality_scorecard"


def test_quality_scorecard_p2p():
    if importlib.util.find_spec(MODULE_PATH) is None:
        pytest.skip("quality scorecard module not available")

    from utils.quality_scorecard import QualitySignal, build_quality_scorecard

    scorecard = build_quality_scorecard(QualitySignal(
        cohort_id="c-10",
        assessments=4,
        avg_score=78,
        remediation_rate=0.2,
    ))

    assert scorecard["risk_band"] == "medium"
