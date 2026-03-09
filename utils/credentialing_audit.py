"""Credentialing audit helpers for enterprise accreditation flows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List


@dataclass(frozen=True)
class CredentialRecord:
    learner_id: str
    credential_id: str
    issued: bool
    verified: bool
    revoked: bool
    issuer: str


@dataclass(frozen=True)
class CredentialAuditSummary:
    total_records: int
    issued_count: int
    verified_count: int
    revoked_count: int
    integrity_score: float


def _percent(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round((value / total) * 100.0, 2)


def summarize_credentials(records: Iterable[CredentialRecord]) -> CredentialAuditSummary:
    rows = list(records)
    total = len(rows)
    if total == 0:
        return CredentialAuditSummary(0, 0, 0, 0, 100.0)

    issued = len([row for row in rows if row.issued])
    verified = len([row for row in rows if row.verified])
    revoked = len([row for row in rows if row.revoked])

    integrity = max(0.0, 100.0 - _percent(revoked, total) - (_percent(issued - verified, total) / 2.0))

    return CredentialAuditSummary(
        total_records=total,
        issued_count=issued,
        verified_count=verified,
        revoked_count=revoked,
        integrity_score=round(integrity, 2),
    )


def issuer_breakdown(records: Iterable[CredentialRecord]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for row in records:
        out[row.issuer] = out.get(row.issuer, 0) + 1
    return out


def high_risk_records(records: Iterable[CredentialRecord]) -> List[str]:
    return [row.learner_id for row in records if row.issued and (row.revoked or not row.verified)]


def verification_gap_by_issuer(records: Iterable[CredentialRecord]) -> Dict[str, float]:
    grouped: Dict[str, Dict[str, int]] = {}
    for row in records:
        if row.issuer not in grouped:
            grouped[row.issuer] = {"issued": 0, "verified": 0}
        if row.issued:
            grouped[row.issuer]["issued"] += 1
        if row.verified:
            grouped[row.issuer]["verified"] += 1

    out: Dict[str, float] = {}
    for issuer, values in grouped.items():
        issued = max(1, values["issued"])
        out[issuer] = round(((issued - values["verified"]) / issued) * 100.0, 2)
    return out


def issuer_risk_ranking(records: Iterable[CredentialRecord]) -> List[str]:
    gaps = verification_gap_by_issuer(records)
    return [name for name, _ in sorted(gaps.items(), key=lambda row: (-row[1], row[0]))]


def audit_digest(records: Iterable[CredentialRecord]) -> Dict[str, object]:
    rows = list(records)
    summary = summarize_credentials(rows)
    return {
        "total_records": summary.total_records,
        "integrity_score": summary.integrity_score,
        "issuer_breakdown": issuer_breakdown(rows),
        "verification_gap_by_issuer": verification_gap_by_issuer(rows),
        "issuer_risk_ranking": issuer_risk_ranking(rows),
        "high_risk_records": high_risk_records(rows),
    }
