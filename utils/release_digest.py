"""Release digest composition helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from utils.compliance_digest import ComplianceDigest
from utils.incident_bridge import IncidentBridgeSnapshot
from utils.rollout_governance import RolloutGovernanceReport


@dataclass(frozen=True)
class ReleaseDigest:
    release_id: str
    approved: bool
    summary: Dict[str, object]


def compose_release_digest(
    release_id: str,
    governance: RolloutGovernanceReport,
    incidents: IncidentBridgeSnapshot,
    compliance: ComplianceDigest,
) -> ReleaseDigest:
    approved = governance.approved and compliance.passed and not incidents.page_on_call

    summary: Dict[str, object] = {
        "governance_approved": governance.approved,
        "governance_blockers": len(governance.blockers),
        "governance_warnings": len(governance.warnings),
        "incident_highest": incidents.highest_severity,
        "incident_total": incidents.total_signals,
        "compliance_passed": compliance.passed,
        "compliance_score": compliance.score,
    }

    return ReleaseDigest(
        release_id=release_id,
        approved=approved,
        summary=summary,
    )


def digest_to_dict(digest: ReleaseDigest) -> Dict[str, object]:
    return {
        "release_id": digest.release_id,
        "approved": digest.approved,
        "summary": dict(digest.summary),
    }
