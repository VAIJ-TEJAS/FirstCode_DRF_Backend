"""
Change Risk & Deployment Gate — server-side evaluation aligned with the React enterpriseRuntime module.

Pure Python (no DB); used by CI tooling and the enterprise change-risk API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, TypedDict

# Mirrors src/lib/enterpriseRuntime/changeRiskThresholds.ts
THRESHOLDS = {
    "high_churn_lines": 2500,
    "many_files": 18,
    "min_new_test_files_for_large_change": 1,
    "min_f2p_for_large_change": 1,
    "min_p2p_for_large_change": 1,
    "migration_heavy": 3,
    "slo_critical_pct": 10,
    "slo_warn_pct": 25,
}

ChangeSurface = Literal["web", "api", "worker", "infra", "data", "content", "mobile", "unknown"]
ChangeEnvironment = Literal["production", "staging", "development"]
RiskBand = Literal["low", "medium", "high", "critical"]
GateVerdict = Literal["pass", "warn", "block"]
IssueSeverity = Literal["info", "warning", "error"]


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def total_touched_lines(added: int, deleted: int) -> int:
    return max(0, added) + max(0, deleted)


def churn_ratio(churn_lines: int, added: int, deleted: int) -> float:
    denom = total_touched_lines(added, deleted)
    if denom <= 0:
        return 0.0
    return float(clamp(churn_lines / denom, 0, 1))


@dataclass(frozen=True)
class ChangeIssue:
    code: str
    severity: IssueSeverity
    message: str
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class ChangeBatchInput:
    batch_id: str
    environment: ChangeEnvironment
    primary_surface: ChangeSurface
    changed_files: int
    added_lines: int
    deleted_lines: int
    churn_lines: int
    new_test_files: int
    f2p_test_files: int
    p2p_test_files: int
    test_regressions: int
    migration_count: int
    major_dependency_bumps: int
    touches_auth: bool
    touches_payments: bool
    touches_security_policy: bool
    breaking_api_change: bool
    has_rollback_plan: bool
    slo_error_budget_remaining_pct: Optional[float] = None
    in_freeze_window: Optional[bool] = None
    oncall_assigned: Optional[bool] = None


@dataclass(frozen=True)
class ChangeScoreBreakdown:
    churn: int
    quality: int
    safety: int
    ops: int
    overall: int


@dataclass(frozen=True)
class ChangeGateDecision:
    batch_id: str
    environment: ChangeEnvironment
    primary_surface: ChangeSurface
    risk_band: RiskBand
    verdict: GateVerdict
    score: ChangeScoreBreakdown
    issues: Tuple[ChangeIssue, ...]
    recommended_actions: Tuple[str, ...]
    generated_at_iso: str


def _score_churn(inp: ChangeBatchInput) -> int:
    s = 100.0
    touched = total_touched_lines(inp.added_lines, inp.deleted_lines)
    ratio = churn_ratio(inp.churn_lines, inp.added_lines, inp.deleted_lines)
    hcl = THRESHOLDS["high_churn_lines"]

    if touched >= hcl:
        s -= 18
    elif touched >= hcl * 0.5:
        s -= 10
    elif touched >= 400:
        s -= 4

    if ratio >= 0.55:
        s -= 12
    elif ratio >= 0.35:
        s -= 6

    if inp.changed_files >= THRESHOLDS["many_files"]:
        s -= 8
    elif inp.changed_files >= 12:
        s -= 4

    return int(clamp(s, 0, 100))


def _score_quality(inp: ChangeBatchInput) -> int:
    s = 100.0
    large = total_touched_lines(inp.added_lines, inp.deleted_lines) >= 800 or inp.changed_files >= 12

    if inp.test_regressions > 0:
        s -= 14 * min(3, inp.test_regressions)

    if large:
        if inp.new_test_files < THRESHOLDS["min_new_test_files_for_large_change"]:
            s -= 16
        if inp.f2p_test_files < THRESHOLDS["min_f2p_for_large_change"]:
            s -= 14
        if inp.p2p_test_files < THRESHOLDS["min_p2p_for_large_change"]:
            s -= 10
    else:
        if inp.new_test_files == 0 and total_touched_lines(inp.added_lines, inp.deleted_lines) >= 200:
            s -= 6

    return int(clamp(s, 0, 100))


def _score_safety(inp: ChangeBatchInput) -> int:
    s = 100.0
    if inp.migration_count >= THRESHOLDS["migration_heavy"]:
        s -= 16
    elif inp.migration_count > 0:
        s -= 6

    if inp.major_dependency_bumps > 0:
        s -= 6 * min(3, inp.major_dependency_bumps)

    if inp.touches_auth:
        s -= 10
    if inp.touches_payments:
        s -= 14
    if inp.touches_security_policy:
        s -= 12
    if inp.breaking_api_change:
        s -= 12
    if not inp.has_rollback_plan:
        s -= 18

    return int(clamp(s, 0, 100))


def _score_ops(inp: ChangeBatchInput) -> int:
    s = 100.0
    budget = inp.slo_error_budget_remaining_pct
    if budget is not None:
        if budget < THRESHOLDS["slo_critical_pct"]:
            s -= 28
        elif budget < THRESHOLDS["slo_warn_pct"]:
            s -= 14
        elif budget < 40:
            s -= 6

    if inp.in_freeze_window:
        s -= 22
    if inp.oncall_assigned is False:
        s -= 10

    return int(clamp(s, 0, 100))


def _round_half_up(x: float) -> int:
    """Match JavaScript Math.round for non-negative values."""
    return int(math.floor(x + 0.5))


def compute_score_breakdown(inp: ChangeBatchInput) -> ChangeScoreBreakdown:
    churn = _score_churn(inp)
    quality = _score_quality(inp)
    safety = _score_safety(inp)
    ops = _score_ops(inp)
    raw = churn * 0.22 + quality * 0.28 + safety * 0.32 + ops * 0.18
    overall = int(clamp(_round_half_up(raw), 0, 100))
    return ChangeScoreBreakdown(churn=churn, quality=quality, safety=safety, ops=ops, overall=overall)


def classify_risk_band(overall_score: int) -> RiskBand:
    if overall_score >= 82:
        return "low"
    if overall_score >= 68:
        return "medium"
    if overall_score >= 52:
        return "high"
    return "critical"


def _mk_issue(
    code: str,
    severity: IssueSeverity,
    message: str,
    evidence: Optional[Dict[str, Any]] = None,
) -> ChangeIssue:
    return ChangeIssue(code=code, severity=severity, message=message, evidence=evidence)


def collect_issues(inp: ChangeBatchInput) -> List[ChangeIssue]:
    issues: List[ChangeIssue] = []
    touched = total_touched_lines(inp.added_lines, inp.deleted_lines)
    large = touched >= 800 or inp.changed_files >= 12

    if touched >= THRESHOLDS["high_churn_lines"]:
        issues.append(
            _mk_issue(
                "high_churn",
                "warning",
                "Very high line churn; consider splitting the change or increasing review capacity.",
                {"touched_lines": touched},
            )
        )

    if large and inp.new_test_files < THRESHOLDS["min_new_test_files_for_large_change"]:
        issues.append(
            _mk_issue(
                "missing_tests",
                "warning",
                "Large change with few new test files.",
                {"new_test_files": inp.new_test_files},
            )
        )
    if large and inp.f2p_test_files < THRESHOLDS["min_f2p_for_large_change"]:
        issues.append(
            _mk_issue(
                "missing_f2p",
                "error",
                "Large change should include F2P-style unit coverage.",
                {"f2p_test_files": inp.f2p_test_files},
            )
        )
    if large and inp.p2p_test_files < THRESHOLDS["min_p2p_for_large_change"]:
        issues.append(
            _mk_issue(
                "missing_p2p",
                "warning",
                "Large change should include P2P-style integration coverage.",
                {"p2p_test_files": inp.p2p_test_files},
            )
        )

    if inp.migration_count >= THRESHOLDS["migration_heavy"]:
        issues.append(
            _mk_issue(
                "migration_risk",
                "warning",
                "Migration-heavy change; verify rollback and data compatibility.",
                {"migration_count": inp.migration_count},
            )
        )

    if inp.touches_auth:
        issues.append(
            _mk_issue(
                "auth_surface",
                "warning",
                "Touches authentication flows; verify security review and session edge cases.",
            )
        )
    if inp.touches_payments:
        issues.append(
            _mk_issue(
                "payment_surface",
                "error",
                "Touches payments; require extra verification and rollback clarity.",
            )
        )
    if inp.touches_security_policy:
        issues.append(
            _mk_issue(
                "security_surface",
                "warning",
                "Touches security-sensitive policy; coordinate review.",
            )
        )
    if inp.breaking_api_change:
        issues.append(
            _mk_issue(
                "breaking_api",
                "warning",
                "Breaking API change; ensure consumers and version notes are covered.",
            )
        )

    if not inp.has_rollback_plan:
        issues.append(_mk_issue("rollback_unclear", "error", "Rollback plan missing or not documented."))

    if inp.major_dependency_bumps > 0:
        issues.append(
            _mk_issue(
                "dependency_major_bump",
                "info",
                "Major dependency bumps detected; watch for transitive breakage.",
                {"major_dependency_bumps": inp.major_dependency_bumps},
            )
        )

    budget = inp.slo_error_budget_remaining_pct
    if budget is not None and budget < THRESHOLDS["slo_critical_pct"]:
        issues.append(
            _mk_issue(
                "slo_budget_critical",
                "error",
                "SLO error budget is critically low.",
                {"slo_error_budget_remaining_pct": budget},
            )
        )

    if inp.in_freeze_window:
        issues.append(_mk_issue("freeze_window", "error", "Change overlaps a freeze window."))
    if inp.oncall_assigned is False:
        issues.append(_mk_issue("oncall_gap", "warning", "On-call coverage not confirmed for this window."))

    return issues


def verdict_from_signals(overall: int, issues: Sequence[ChangeIssue]) -> GateVerdict:
    has_error = any(i.severity == "error" for i in issues)
    if has_error and overall < 60:
        return "block"
    if has_error:
        return "warn"
    if overall < 55:
        return "block"
    if overall < 72:
        return "warn"
    return "pass"


def recommend_actions(inp: ChangeBatchInput, issues: Sequence[ChangeIssue]) -> List[str]:
    codes = {i.code for i in issues}
    actions: List[str] = []

    if "missing_f2p" in codes or "missing_tests" in codes:
        actions.append("Add focused F2P tests for new logic and edge cases.")
    if "missing_p2p" in codes:
        actions.append("Add P2P tests for critical flows affected by this batch.")
    if "high_churn" in codes:
        actions.append("Split the change into smaller deployable slices or add staged rollout.")
    if "migration_risk" in codes:
        actions.append("Validate migrations in staging; plan additive phases if possible.")
    if "payment_surface" in codes:
        actions.append("Run payment verification in staging; double-check idempotency and rollback.")
    if "auth_surface" in codes:
        actions.append("Exercise login/session flows in staging; watch token and cookie edge cases.")
    if "rollback_unclear" in codes:
        actions.append("Document rollback steps and validate them against the release artifact.")
    if "slo_budget_critical" in codes:
        actions.append("Defer non-urgent changes until error budget recovers.")
    if "freeze_window" in codes:
        actions.append("Reschedule outside the freeze window or obtain an explicit exception.")
    if "oncall_gap" in codes:
        actions.append("Assign on-call primary + backup before deploying.")

    if not actions:
        actions.append("Proceed with normal release checks; keep monitoring and rollback ready.")
    return actions


def evaluate_change_batch(inp: ChangeBatchInput, now_iso: str) -> ChangeGateDecision:
    score = compute_score_breakdown(inp)
    risk_band = classify_risk_band(score.overall)
    issues = collect_issues(inp)
    verdict = verdict_from_signals(score.overall, issues)
    rec = recommend_actions(inp, issues)
    return ChangeGateDecision(
        batch_id=inp.batch_id,
        environment=inp.environment,
        primary_surface=inp.primary_surface,
        risk_band=risk_band,
        verdict=verdict,
        score=score,
        issues=tuple(issues),
        recommended_actions=tuple(rec),
        generated_at_iso=now_iso,
    )


class _IssueDict(TypedDict, total=False):
    code: str
    severity: str
    message: str
    evidence: Dict[str, Any]


class _ScoreDict(TypedDict):
    churn: int
    quality: int
    safety: int
    ops: int
    overall: int


class ChangeGateDecisionDict(TypedDict):
    batchId: str
    environment: str
    primarySurface: str
    riskBand: str
    verdict: str
    score: _ScoreDict
    issues: List[_IssueDict]
    recommendedActions: List[str]
    generatedAtISO: str


def issue_to_dict(i: ChangeIssue) -> _IssueDict:
    d: _IssueDict = {"code": i.code, "severity": i.severity, "message": i.message}
    if i.evidence is not None:
        d["evidence"] = i.evidence
    return d


def decision_to_camel_dict(d: ChangeGateDecision) -> ChangeGateDecisionDict:
    return {
        "batchId": d.batch_id,
        "environment": d.environment,
        "primarySurface": d.primary_surface,
        "riskBand": d.risk_band,
        "verdict": d.verdict,
        "score": {
            "churn": d.score.churn,
            "quality": d.score.quality,
            "safety": d.score.safety,
            "ops": d.score.ops,
            "overall": d.score.overall,
        },
        "issues": [issue_to_dict(i) for i in d.issues],
        "recommendedActions": list(d.recommended_actions),
        "generatedAtISO": d.generated_at_iso,
    }


_ENV = frozenset({"production", "staging", "development"})
_SURFACE = frozenset({"web", "api", "worker", "infra", "data", "content", "mobile", "unknown"})


def parse_batch_from_json(data: Dict[str, Any]) -> ChangeBatchInput:
    """Parse a camelCase JSON body (same keys as the React ChangeBatchInput)."""
    missing = [k for k in _REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")

    env = data["environment"]
    if env not in _ENV:
        raise ValueError(f"Invalid environment: {env!r}")

    surf = data["primarySurface"]
    if surf not in _SURFACE:
        raise ValueError(f"Invalid primarySurface: {surf!r}")

    return ChangeBatchInput(
        batch_id=str(data["batchId"]),
        environment=env,  # type: ignore[arg-type]
        primary_surface=surf,  # type: ignore[arg-type]
        changed_files=int(data["changedFiles"]),
        added_lines=int(data["addedLines"]),
        deleted_lines=int(data["deletedLines"]),
        churn_lines=int(data["churnLines"]),
        new_test_files=int(data["newTestFiles"]),
        f2p_test_files=int(data["f2pTestFiles"]),
        p2p_test_files=int(data["p2pTestFiles"]),
        test_regressions=int(data["testRegressions"]),
        migration_count=int(data["migrationCount"]),
        major_dependency_bumps=int(data["majorDependencyBumps"]),
        touches_auth=bool(data["touchesAuth"]),
        touches_payments=bool(data["touchesPayments"]),
        touches_security_policy=bool(data["touchesSecurityPolicy"]),
        breaking_api_change=bool(data["breakingApiChange"]),
        has_rollback_plan=bool(data["hasRollbackPlan"]),
        slo_error_budget_remaining_pct=_optional_float(data.get("sloErrorBudgetRemainingPct")),
        in_freeze_window=_optional_bool(data.get("inFreezeWindow")),
        oncall_assigned=_optional_bool(data.get("oncallAssigned")),
    )


_REQUIRED_KEYS = frozenset(
    {
        "batchId",
        "environment",
        "primarySurface",
        "changedFiles",
        "addedLines",
        "deletedLines",
        "churnLines",
        "newTestFiles",
        "f2pTestFiles",
        "p2pTestFiles",
        "testRegressions",
        "migrationCount",
        "majorDependencyBumps",
        "touchesAuth",
        "touchesPayments",
        "touchesSecurityPolicy",
        "breakingApiChange",
        "hasRollbackPlan",
    }
)


def _optional_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    return float(v)


def _optional_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    return bool(v)
