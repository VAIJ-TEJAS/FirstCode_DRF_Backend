from __future__ import annotations

from utils.change_risk_gate import parse_batch_from_json
from utils.change_risk_gate import evaluate_change_batch as evaluate

from tests.change_risk_fixtures import (
    BATCH_FREEZE_LOW_BUDGET,
    BATCH_HEALTHY,
    BATCH_LARGE_THIN_TESTS,
    BATCH_MIGRATION_HEAVY,
    BATCH_PAYMENTS_NO_ROLLBACK,
)


def test_p2p_cr_010_golden_verdicts_match_frontend_regression() -> None:
    """Aligned with changeRisk.regression.p2p.test.ts golden assertions."""
    iso = "2026-03-14T10:00:00.000Z"
    assert evaluate(parse_batch_from_json(BATCH_HEALTHY), iso).verdict == "pass"
    assert evaluate(parse_batch_from_json(BATCH_LARGE_THIN_TESTS), iso).verdict == "warn"
    assert evaluate(parse_batch_from_json(BATCH_PAYMENTS_NO_ROLLBACK), iso).verdict == "warn"
    assert evaluate(parse_batch_from_json(BATCH_FREEZE_LOW_BUDGET), iso).verdict == "warn"
    assert evaluate(parse_batch_from_json(BATCH_MIGRATION_HEAVY), iso).verdict == "pass"


def test_p2p_cr_011_freeze_batch_has_ops_cluster_issues() -> None:
    d = evaluate(parse_batch_from_json(BATCH_FREEZE_LOW_BUDGET), "2026-03-14T10:00:00.000Z")
    codes = {i.code for i in d.issues}
    assert "freeze_window" in codes
    assert "slo_budget_critical" in codes
    assert "oncall_gap" in codes
