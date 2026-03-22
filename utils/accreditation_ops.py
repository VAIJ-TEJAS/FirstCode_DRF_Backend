"""
Accreditation Ops Matrix — evaluates evidence submission coverage against the catalog JSON.
Aligned with React `accreditationOps*` modules.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple, TypedDict

THRESHOLDS = {
    "domain_weak_overall": 62,
    "domain_weak_local": 55,
    "low_confidence_avg": 0.62,
    "sparse_submission_ratio": 0.12,
    "weight_skew_ratio": 0.35,
}


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def status_to_unit_score(status: str) -> float:
    if status == "complete":
        return 1.0
    if status == "partial":
        return 0.58
    return 0.0


def clamp01(v: float) -> float:
    return clamp(v, 0.0, 1.0)


@dataclass(frozen=True)
class EvidenceRow:
    id: str
    title: str
    domain: str
    tier: str
    weight: float
    checklist: Tuple[str, ...]
    narrative: str


_CATALOG_CACHE: Optional[List[EvidenceRow]] = None


def _catalog_path() -> Path:
    return Path(__file__).resolve().parent / "data" / "accreditation_evidence_catalog.json"


def load_evidence_catalog() -> List[EvidenceRow]:
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    raw = json.loads(_catalog_path().read_text(encoding="utf-8"))
    rows: List[EvidenceRow] = []
    for item in raw:
        rows.append(
            EvidenceRow(
                id=str(item["id"]),
                title=str(item["title"]),
                domain=str(item["domain"]),
                tier=str(item["tier"]),
                weight=float(item["weight"]),
                checklist=tuple(str(x) for x in item["checklist"]),
                narrative=str(item["narrative"]),
            )
        )
    _CATALOG_CACHE = rows
    return rows


def build_index(rows: Sequence[EvidenceRow]) -> Dict[str, EvidenceRow]:
    return {r.id: r for r in rows}


class SubmissionItem(TypedDict):
    status: str
    confidence: float


def weighted_item_score(row: EvidenceRow, submission: Dict[str, SubmissionItem]) -> Tuple[float, float]:
    sub = submission.get(row.id)
    if not sub:
        return 0.0, 0.0
    unit = status_to_unit_score(sub["status"]) * clamp01(float(sub["confidence"]))
    return unit, clamp01(float(sub["confidence"]))


def evaluate_accreditation_submission(
    catalog: List[EvidenceRow],
    submission: Dict[str, SubmissionItem],
    institution_id: str,
    cycle_label: str,
    now_iso: str,
) -> Dict[str, Any]:
    idx = build_index(catalog)
    domain_agg: Dict[str, Dict[str, float]] = {}
    tier_agg: Dict[str, Dict[str, float]] = {}

    def push_agg(target: Dict[str, Dict[str, float]], key: str, weight: float, unit: float) -> None:
        cur = target.setdefault(key, {"num": 0.0, "den": 0.0, "n": 0.0})
        cur["num"] += weight * unit
        cur["den"] += weight
        cur["n"] += 1.0

    num = 0.0
    den = 0.0
    conf_sum = 0.0
    conf_n = 0.0

    for row in catalog:
        unit, conf = weighted_item_score(row, submission)
        num += row.weight * unit
        den += row.weight
        conf_sum += conf
        conf_n += 1.0
        push_agg(domain_agg, row.domain, row.weight, unit)
        push_agg(tier_agg, row.tier, row.weight, unit)

    coverage = clamp((num / den) * 100, 0, 100) if den > 0 else 0.0
    confidence = clamp01(conf_sum / conf_n) if conf_n > 0 else 0.0
    overall = round_half_up(clamp(coverage * 0.72 + confidence * 100 * 0.28, 0, 100))

    def rollup_to_list(agg: Dict[str, Dict[str, float]], kind: str) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for k in sorted(agg.keys()):
            v = agg[k]
            ws = clamp((v["num"] / v["den"]) * 100, 0, 100) if v["den"] > 0 else 0.0
            if kind == "domain":
                out.append({"domain": k, "weightedScore": ws, "weightSum": v["den"], "itemCount": int(v["n"])})
            else:
                out.append({"tier": k, "weightedScore": ws, "weightSum": v["den"], "itemCount": int(v["n"])})
        return out

    domain_rollups = rollup_to_list(domain_agg, "domain")
    tier_rollups = rollup_to_list(tier_agg, "tier")

    domain_worst: Optional[str] = None
    tier_worst: Optional[str] = None
    wds = 101.0
    wts = 101.0
    for d in domain_rollups:
        if d["weightedScore"] < wds:
            wds = d["weightedScore"]
            domain_worst = d["domain"]
    for t in tier_rollups:
        if t["weightedScore"] < wts:
            wts = t["weightedScore"]
            tier_worst = t["tier"]

    score = {
        "overall": overall,
        "coverage": round_half_up(coverage),
        "confidence": round_half_up(confidence * 100),
        "domainWorst": domain_worst,
        "tierWorst": tier_worst,
    }

    issues = _collect_issues(catalog, submission, score, domain_rollups, tier_rollups, idx, confidence)
    actions = _build_actions(issues, domain_rollups, tier_rollups)

    evaluated_keys = sum(1 for k in submission if k in idx)

    return {
        "institutionId": institution_id,
        "cycleLabel": cycle_label,
        "score": score,
        "domainRollups": domain_rollups,
        "tierRollups": tier_rollups,
        "issues": issues,
        "recommendedActions": actions,
        "catalogSize": len(catalog),
        "evaluatedEvidenceIds": evaluated_keys,
        "generatedAtISO": now_iso,
    }


def _collect_issues(
    catalog: List[EvidenceRow],
    submission: Dict[str, SubmissionItem],
    score: Dict[str, Any],
    domain_rollups: List[Dict[str, Any]],
    tier_rollups: List[Dict[str, Any]],
    idx: Dict[str, EvidenceRow],
    avg_confidence: float,
) -> List[Dict[str, Any]]:
    issues: List[Dict[str, Any]] = []
    submitted = set(submission.keys())

    for eid in submitted:
        if eid not in idx:
            issues.append(
                {
                    "code": "catalog_gap",
                    "severity": "warning",
                    "message": f"Submission references unknown evidence id: {eid}.",
                    "evidence": {"evidenceId": eid},
                }
            )

    if avg_confidence < THRESHOLDS["low_confidence_avg"]:
        issues.append(
            {
                "code": "low_confidence_cluster",
                "severity": "warning",
                "message": "Average confidence across submitted items is low.",
                "evidence": {"avgConfidence": round_half_up(avg_confidence * 100)},
            }
        )

    ratio = len(submitted) / max(1, len(catalog))
    if ratio < THRESHOLDS["sparse_submission_ratio"]:
        issues.append(
            {
                "code": "submission_sparse",
                "severity": "error",
                "message": "Sparse submission relative to catalog coverage expectations.",
                "evidence": {"submissionRatio": round_half_up(ratio * 100)},
            }
        )

    if score["overall"] < THRESHOLDS["domain_weak_overall"]:
        for d in [x for x in domain_rollups if x["weightedScore"] < THRESHOLDS["domain_weak_local"]][:4]:
            issues.append(
                {
                    "code": "domain_weak",
                    "severity": "warning",
                    "message": f'Domain "{d["domain"]}" is below readiness threshold.',
                    "evidence": {"domain": d["domain"], "weightedScore": round_half_up(d["weightedScore"])},
                }
            )

    for t in [x for x in tier_rollups if x["weightedScore"] < THRESHOLDS["domain_weak_local"]][:3]:
        issues.append(
            {
                "code": "tier_weak",
                "severity": "info",
                "message": f'Tier "{t["tier"]}" is trailing other maturity tiers.',
                "evidence": {"tier": t["tier"], "weightedScore": round_half_up(t["weightedScore"])},
            }
        )

    weight_by_domain: Dict[str, float] = {}
    for row in catalog:
        weight_by_domain[row.domain] = weight_by_domain.get(row.domain, 0.0) + row.weight
    total_w = sum(weight_by_domain.values())
    if total_w > 0:
        for d, w in weight_by_domain.items():
            if w / total_w > THRESHOLDS["weight_skew_ratio"]:
                issues.append(
                    {
                        "code": "weight_skew",
                        "severity": "info",
                        "message": "Catalog weight is concentrated in a single domain; review for balance.",
                        "evidence": {"domain": d, "weightShare": round_half_up((w / total_w) * 100)},
                    }
                )
                break

    return issues


def _build_actions(
    issues: List[Dict[str, Any]],
    domain_rollups: List[Dict[str, Any]],
    tier_rollups: List[Dict[str, Any]],
) -> List[str]:
    codes = {i["code"] for i in issues}
    actions: List[str] = []
    if "submission_sparse" in codes:
        actions.append("Expand evidence collection to cover additional catalog rows before audit window closes.")
        actions.append("Prioritize high-weight domains first; automate evidence pulls from systems of record.")
    if "low_confidence_cluster" in codes:
        actions.append("Run spot audits on a sample of evidence items; attach primary sources and approver sign-offs.")
    if "domain_weak" in codes:
        weak = [d["domain"] for d in domain_rollups if d["weightedScore"] < 60][:5]
        if weak:
            actions.append(f"Strengthen weakest domains: {', '.join(weak)}.")
    if "tier_weak" in codes:
        ts = [t["tier"] for t in tier_rollups if t["weightedScore"] < 60][:4]
        if ts:
            actions.append(f"Address maturity gaps in tiers: {', '.join(ts)}.")
    if "catalog_gap" in codes:
        actions.append("Remove unknown evidence IDs from submission or sync catalog version with evaluator.")
    if "weight_skew" in codes:
        actions.append("Balance narrative across domains; avoid over-indexing on a single compliance area.")
    if not actions:
        actions.append("Maintain evidence hygiene; schedule quarterly steering reviews against the catalog.")
    return actions


def parse_submission_payload(data: Dict[str, Any]) -> Tuple[str, str, Dict[str, SubmissionItem]]:
    missing = [k for k in ("institutionId", "cycleLabel", "submission") if k not in data]
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")
    sub_raw = data["submission"]
    if not isinstance(sub_raw, dict):
        raise ValueError("submission must be an object")
    out: Dict[str, SubmissionItem] = {}
    for k, v in sub_raw.items():
        if not isinstance(v, dict) or "status" not in v or "confidence" not in v:
            raise ValueError(f"Invalid submission item for {k!r}")
        out[str(k)] = {"status": str(v["status"]), "confidence": float(v["confidence"])}
    return str(data["institutionId"]), str(data["cycleLabel"]), out
