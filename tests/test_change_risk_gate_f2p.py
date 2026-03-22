from __future__ import annotations

from utils.change_risk_gate import (
    ChangeBatchInput,
    churn_ratio,
    clamp,
    collect_issues,
    compute_score_breakdown,
    parse_batch_from_json,
    total_touched_lines,
    verdict_from_signals,
)
from utils.change_risk_gate import evaluate_change_batch as evaluate

from tests.change_risk_fixtures import BATCH_HEALTHY, BATCH_LARGE_THIN_TESTS


def test_f2p_cr_001_clamp_bounds() -> None:
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(99, 0, 10) == 10


def test_f2p_cr_002_touched_and_churn_ratio() -> None:
    assert total_touched_lines(100, 50) == 150
    assert churn_ratio(0, 100, 100) == 0.0
    assert abs(churn_ratio(100, 100, 100) - 100 / 200) < 1e-9


def test_f2p_cr_003_parse_batch_roundtrip() -> None:
    batch = parse_batch_from_json(BATCH_HEALTHY)
    assert isinstance(batch, ChangeBatchInput)
    assert batch.batch_id == "batch-healthy"


def test_f2p_cr_004_invalid_environment_rejected() -> None:
    bad = {**BATCH_HEALTHY, "environment": "prod"}
    try:
        parse_batch_from_json(bad)
    except ValueError as e:
        assert "Invalid environment" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_f2p_cr_005_healthy_batch_passes_gate() -> None:
    batch = parse_batch_from_json(BATCH_HEALTHY)
    d = evaluate(batch, "2026-03-14T10:00:00.000Z")
    assert d.verdict == "pass"
    assert d.risk_band in {"low", "medium"}


def test_f2p_cr_006_large_change_missing_f2p_error() -> None:
    batch = parse_batch_from_json(BATCH_LARGE_THIN_TESTS)
    issues = collect_issues(batch)
    codes = [i.code for i in issues]
    assert "missing_f2p" in codes
    assert any(i.severity == "error" for i in issues)


def test_f2p_cr_007_verdict_rules_errors_high_score_warn() -> None:
    from utils.change_risk_gate import ChangeIssue

    issues = (ChangeIssue(code="payment_surface", severity="error", message="x"),)
    assert verdict_from_signals(88, issues) == "warn"


def test_f2p_cr_008_score_breakdown_shape() -> None:
    batch = parse_batch_from_json(BATCH_HEALTHY)
    s = compute_score_breakdown(batch)
    for k in ("churn", "quality", "safety", "ops", "overall"):
        v = getattr(s, k)
        assert 0 <= v <= 100
