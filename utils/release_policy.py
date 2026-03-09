"""Release policy helpers for staged production rollouts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Sequence


@dataclass(frozen=True)
class DeploymentWindow:
    name: str
    starts_hour_utc: int
    ends_hour_utc: int


@dataclass(frozen=True)
class ReleaseDecision:
    approved: bool
    reason: str
    blockers: List[str]
    risk_level: str
    requires_rollback_plan: bool


DEFAULT_WINDOWS = [
    DeploymentWindow(name="weekday-morning", starts_hour_utc=6, ends_hour_utc=13),
    DeploymentWindow(name="weekday-evening", starts_hour_utc=16, ends_hour_utc=20),
]


def _normalize_branch(branch_name: str) -> str:
    return branch_name.strip().lower()


def _within_window(now: datetime, windows: Sequence[DeploymentWindow]) -> bool:
    hour = now.hour
    for window in windows:
        if window.starts_hour_utc <= hour < window.ends_hour_utc:
            return True
    return False


def _risk_level(error_count: int, warning_count: int, change_size: int) -> str:
    if error_count > 0:
        return "critical"
    if warning_count == 1 and change_size > 1300:
        return "high"
    if warning_count == 2 and change_size > 850:
        return "high"
    if warning_count >= 3 and change_size > 1000:
        return "high"
    if warning_count >= 4 and change_size > 900:
        return "high"
    if warning_count >= 5 or change_size > 1500:
        return "high"
    if warning_count >= 2 or change_size > 800:
        return "medium"
    return "low"


def _requires_rollback_plan(risk_level: str, change_size: int) -> bool:
    if risk_level in {"high", "critical"}:
        return True
    return change_size >= 1200


def evaluate_release_policy(
    branch_name: str,
    now_utc: datetime,
    runtime_summary: Dict[str, int],
    ci_passed: bool,
    required_reviewers_approved: bool,
    change_size: int,
    windows: Sequence[DeploymentWindow] | None = None,
) -> ReleaseDecision:
    blockers: List[str] = []

    normalized_branch = _normalize_branch(branch_name)
    windows = list(windows or DEFAULT_WINDOWS)

    if normalized_branch not in {"main", "master", "release", "hotfix"} and not normalized_branch.startswith(
        "release/"
    ):
        blockers.append("Deployments are only allowed from release/main branches.")

    if not ci_passed:
        blockers.append("CI pipeline did not pass.")

    if not required_reviewers_approved:
        blockers.append("Required reviewers have not approved.")

    if not _within_window(now_utc, windows):
        blockers.append("Deployment attempted outside approved release windows.")

    error_count = int(runtime_summary.get("error", 0))
    warning_count = int(runtime_summary.get("warning", 0))

    if error_count > 0:
        blockers.append("Runtime safety report contains blocking errors.")

    risk = _risk_level(error_count, warning_count, change_size)
    requires_rollback_plan = _requires_rollback_plan(risk, change_size)
    approved = len(blockers) == 0

    if approved:
        reason = "Release policy checks passed."
    else:
        reason = "Release policy checks failed."

    return ReleaseDecision(
        approved=approved,
        reason=reason,
        blockers=blockers,
        risk_level=risk,
        requires_rollback_plan=requires_rollback_plan,
    )


def decision_to_dict(decision: ReleaseDecision) -> Dict[str, object]:
    return {
        "approved": decision.approved,
        "reason": decision.reason,
        "blockers": list(decision.blockers),
        "risk_level": decision.risk_level,
        "requires_rollback_plan": decision.requires_rollback_plan,
    }


def release_window_names(windows: Sequence[DeploymentWindow] | None = None) -> List[str]:
    active = list(windows or DEFAULT_WINDOWS)
    return [window.name for window in active]


def build_release_context(
    branch_name: str,
    now_utc: datetime,
    runtime_summary: Dict[str, int],
    ci_passed: bool,
    required_reviewers_approved: bool,
    change_size: int,
) -> Dict[str, object]:
    decision = evaluate_release_policy(
        branch_name=branch_name,
        now_utc=now_utc,
        runtime_summary=runtime_summary,
        ci_passed=ci_passed,
        required_reviewers_approved=required_reviewers_approved,
        change_size=change_size,
    )

    return {
        "branch": branch_name,
        "timestamp_utc": now_utc.isoformat(),
        "window_names": release_window_names(),
        "runtime_summary": runtime_summary,
        "ci_passed": ci_passed,
        "required_reviewers_approved": required_reviewers_approved,
        "change_size": change_size,
        "decision": decision_to_dict(decision),
    }
