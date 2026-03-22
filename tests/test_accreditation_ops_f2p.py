from __future__ import annotations

from utils.accreditation_ops import evaluate_accreditation_submission, load_evidence_catalog


def test_f2p_acc_001_catalog_loads() -> None:
    c = load_evidence_catalog()
    assert len(c) >= 1000


def test_f2p_acc_002_dense_submission_scores() -> None:
    catalog = load_evidence_catalog()[:120]
    submission = {row.id: {"status": "complete", "confidence": 0.92} for row in catalog}
    r = evaluate_accreditation_submission(catalog, submission, "i1", "2026-Q1", "2026-03-22T12:00:00.000Z")
    assert r["score"]["overall"] >= 85


def test_f2p_acc_003_unknown_id() -> None:
    catalog = load_evidence_catalog()[:40]
    submission = {catalog[0].id: {"status": "complete", "confidence": 1.0}, "AEV-99999": {"status": "complete", "confidence": 1.0}}
    r = evaluate_accreditation_submission(catalog, submission, "i2", "2026-Q1", "2026-03-22T12:00:00.000Z")
    assert any(i["code"] == "catalog_gap" for i in r["issues"])
