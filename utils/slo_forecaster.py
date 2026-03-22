"""
SLO burn-rate & error-budget forecasting — aligned with React `sloForecaster*` modules.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple, TypedDict

THRESHOLDS = {
    "min_window_hours": 0.25,
    "min_events_for_confidence": 30,
    "budget_critical_pct": 8,
    "budget_low_pct": 22,
    "burn_warm_above": 1.0,
    "burn_hot_above": 2.0,
    "tier_green_min": 82,
    "tier_yellow_min": 68,
    "tier_orange_min": 48,
    "burn_excess_epsilon": 0.02,
}

SloRiskTier = Literal["green", "yellow", "orange", "red"]
SloWindowKind = Literal["1h", "6h", "24h", "7d", "30d"]
IssueSeverity = Literal["info", "warning", "error"]

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def round_half_up(x: float) -> int:
    return int(math.floor(x + 0.5))


def total_events(good: int, bad: int) -> int:
    return max(0, good) + max(0, bad)


@dataclass(frozen=True)
class SloForecastIssue:
    code: str
    severity: IssueSeverity
    message: str
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class SloForecastInput:
    service_id: str
    slo_target_availability_pct: float
    window_kind: SloWindowKind
    window_hours: float
    good_events: int
    bad_events: int
    error_budget_remaining_pct: float


@dataclass(frozen=True)
class SloForecastMetrics:
    total_events: int
    observed_bad_share_pct: float
    max_bad_share_pct: float
    burn_multiple: float
    events_per_hour: float
    bad_events_per_hour: float
    sustainable_bad_events_per_hour: float
    projected_exhaustion_hours: Optional[int]


@dataclass(frozen=True)
class SloForecastScoreBreakdown:
    budget: int
    velocity: int
    overall: int


@dataclass(frozen=True)
class SloForecastResult:
    service_id: str
    window_kind: SloWindowKind
    error_budget_remaining_pct: float
    slo_target_availability_pct: float
    risk_tier: SloRiskTier
    score: SloForecastScoreBreakdown
    metrics: SloForecastMetrics
    issues: Tuple[SloForecastIssue, ...]
    recommended_actions: Tuple[str, ...]
    generated_at_iso: str


def compute_max_bad_share_pct(slo_target_availability_pct: float) -> float:
    return float(clamp(100 - slo_target_availability_pct, 0, 100))


def compute_metrics(inp: SloForecastInput) -> SloForecastMetrics:
    te = total_events(inp.good_events, inp.bad_events)
    max_bad_share_pct = compute_max_bad_share_pct(inp.slo_target_availability_pct)
    observed_bad_share_pct = (inp.bad_events / te) * 100 if te > 0 else 0.0
    burn_multiple = observed_bad_share_pct / max_bad_share_pct if max_bad_share_pct > 0 else 0.0

    wh = max(inp.window_hours, 1e-9)
    events_per_hour = te / wh
    bad_events_per_hour = inp.bad_events / wh
    sustainable_bad_events_per_hour = events_per_hour * (max_bad_share_pct / 100.0)

    projected: Optional[int] = None
    if te > 0 and max_bad_share_pct > 0:
        excess = max(0.0, burn_multiple - 1.0)
        if excess > THRESHOLDS["burn_excess_epsilon"]:
            scale = inp.error_budget_remaining_pct / 100.0
            raw = (scale * wh) / max(excess, THRESHOLDS["burn_excess_epsilon"])
            projected = round_half_up(clamp(raw, 0, 1e6))

    return SloForecastMetrics(
        total_events=te,
        observed_bad_share_pct=observed_bad_share_pct,
        max_bad_share_pct=max_bad_share_pct,
        burn_multiple=burn_multiple,
        events_per_hour=events_per_hour,
        bad_events_per_hour=bad_events_per_hour,
        sustainable_bad_events_per_hour=sustainable_bad_events_per_hour,
        projected_exhaustion_hours=projected,
    )


def score_budget(remaining_pct: float) -> int:
    if remaining_pct < THRESHOLDS["budget_critical_pct"]:
        return 0
    s = 100.0
    if remaining_pct < THRESHOLDS["budget_low_pct"]:
        s -= 22
    elif remaining_pct < 45:
        s -= 10
    return int(clamp(s, 0, 100))


def score_velocity(burn_multiple: float) -> int:
    s = 100.0
    if burn_multiple > THRESHOLDS["burn_hot_above"]:
        s -= 35
    elif burn_multiple > THRESHOLDS["burn_warm_above"]:
        s -= 18
    elif burn_multiple > THRESHOLDS["burn_warm_above"] * 0.85:
        s -= 6
    return int(clamp(s, 0, 100))


def compute_score_breakdown(inp: SloForecastInput, metrics: SloForecastMetrics) -> SloForecastScoreBreakdown:
    if metrics.total_events == 0 or metrics.max_bad_share_pct <= 0:
        return SloForecastScoreBreakdown(budget=0, velocity=0, overall=0)
    budget = score_budget(inp.error_budget_remaining_pct)
    velocity = score_velocity(metrics.burn_multiple)
    overall = round_half_up(clamp(budget * 0.55 + velocity * 0.45, 0, 100))
    return SloForecastScoreBreakdown(budget=budget, velocity=velocity, overall=overall)


def classify_risk_tier(overall: int) -> SloRiskTier:
    if overall >= THRESHOLDS["tier_green_min"]:
        return "green"
    if overall >= THRESHOLDS["tier_yellow_min"]:
        return "yellow"
    if overall >= THRESHOLDS["tier_orange_min"]:
        return "orange"
    return "red"


def _mk_issue(
    code: str,
    severity: IssueSeverity,
    message: str,
    evidence: Optional[Dict[str, Any]] = None,
) -> SloForecastIssue:
    return SloForecastIssue(code=code, severity=severity, message=message, evidence=evidence)


def collect_issues(inp: SloForecastInput, metrics: SloForecastMetrics) -> List[SloForecastIssue]:
    issues: List[SloForecastIssue] = []

    if inp.window_hours < THRESHOLDS["min_window_hours"]:
        issues.append(
            _mk_issue(
                "window_too_short",
                "warning",
                "Observation window is very short; treat burn metrics as noisy.",
                {"window_hours": inp.window_hours},
            )
        )

    if metrics.total_events == 0:
        issues.append(
            _mk_issue(
                "no_traffic",
                "error",
                "No events in window; cannot evaluate SLO burn.",
                {"service_id": inp.service_id},
            )
        )
    elif metrics.total_events < THRESHOLDS["min_events_for_confidence"]:
        issues.append(
            _mk_issue(
                "sparse_signal",
                "warning",
                "Low event volume; confidence in burn multiple is limited.",
                {"total_events": metrics.total_events},
            )
        )

    if metrics.max_bad_share_pct <= 0:
        issues.append(
            _mk_issue(
                "slo_misconfigured",
                "error",
                "SLO target implies zero error budget; check sloTargetAvailabilityPct.",
                {"slo_target_availability_pct": inp.slo_target_availability_pct},
            )
        )

    if inp.error_budget_remaining_pct < THRESHOLDS["budget_critical_pct"]:
        issues.append(
            _mk_issue(
                "budget_critical",
                "error",
                "Error budget remaining is critically low.",
                {"error_budget_remaining_pct": inp.error_budget_remaining_pct},
            )
        )
    elif inp.error_budget_remaining_pct < THRESHOLDS["budget_low_pct"]:
        issues.append(
            _mk_issue(
                "budget_low",
                "warning",
                "Error budget is low; reduce change risk and incident load.",
                {"error_budget_remaining_pct": inp.error_budget_remaining_pct},
            )
        )

    if metrics.burn_multiple > THRESHOLDS["burn_hot_above"]:
        issues.append(
            _mk_issue(
                "burn_hot",
                "error",
                "Burn rate is far above sustainable for this SLO target.",
                {"burn_multiple": metrics.burn_multiple},
            )
        )
    elif metrics.burn_multiple > THRESHOLDS["burn_warm_above"]:
        issues.append(
            _mk_issue(
                "burn_warm",
                "warning",
                "Burn rate exceeds sustainable envelope.",
                {"burn_multiple": metrics.burn_multiple},
            )
        )

    return issues


def build_recommended_actions(
    issues: Sequence[SloForecastIssue],
    metrics: SloForecastMetrics,
) -> List[str]:
    codes = {i.code for i in issues}
    actions: List[str] = []

    if "no_traffic" in codes:
        actions.append("Verify telemetry wiring and sampling; confirm good/bad event counters are populated.")
    if "slo_misconfigured" in codes:
        actions.append("Set a realistic availability target (e.g. 99.9%) so a non-zero error budget exists.")
    if "burn_hot" in codes or "burn_warm" in codes:
        actions.append("Prioritize reliability work: reduce error rate, add guardrails, or temporarily freeze risky deploys.")
        actions.append("Compare burn multiple across shorter and longer windows to rule out spikes vs sustained drift.")
    if "budget_critical" in codes or "budget_low" in codes:
        actions.append("Treat releases as high risk; require explicit leadership approval for non-incident changes.")
    if "sparse_signal" in codes or "window_too_short" in codes:
        actions.append("Extend the observation window or aggregate more services before automating decisions.")

    if metrics.projected_exhaustion_hours is not None and metrics.projected_exhaustion_hours < 72:
        actions.append("Budget may exhaust within 72h at current burn; page on-call and prepare incident comms templates.")

    if not actions:
        actions.append("Maintain current burn; keep dashboards and paging policies aligned with SLO targets.")

    return actions


def evaluate_slo_forecast(inp: SloForecastInput, now_iso: str) -> SloForecastResult:
    metrics = compute_metrics(inp)
    score = compute_score_breakdown(inp, metrics)
    risk_tier = classify_risk_tier(score.overall)
    issues = collect_issues(inp, metrics)
    actions = build_recommended_actions(issues, metrics)

    return SloForecastResult(
        service_id=inp.service_id,
        window_kind=inp.window_kind,
        error_budget_remaining_pct=inp.error_budget_remaining_pct,
        slo_target_availability_pct=inp.slo_target_availability_pct,
        risk_tier=risk_tier,
        score=score,
        metrics=metrics,
        issues=tuple(issues),
        recommended_actions=tuple(actions),
        generated_at_iso=now_iso,
    )


class _IssueDict(TypedDict, total=False):
    code: str
    severity: str
    message: str
    evidence: Dict[str, Any]


class _ScoreDict(TypedDict):
    budget: int
    velocity: int
    overall: int


class _MetricsDict(TypedDict):
    totalEvents: int
    observedBadSharePct: float
    maxBadSharePct: float
    burnMultiple: float
    eventsPerHour: float
    badEventsPerHour: float
    sustainableBadEventsPerHour: float
    projectedExhaustionHours: Optional[int]


class SloForecastResultDict(TypedDict):
    serviceId: str
    windowKind: str
    errorBudgetRemainingPct: float
    sloTargetAvailabilityPct: float
    riskTier: str
    score: _ScoreDict
    metrics: _MetricsDict
    issues: List[_IssueDict]
    recommendedActions: List[str]
    generatedAtISO: str


def issue_to_dict(i: SloForecastIssue) -> _IssueDict:
    d: _IssueDict = {"code": i.code, "severity": i.severity, "message": i.message}
    if i.evidence is not None:
        d["evidence"] = i.evidence
    return d


def result_to_camel_dict(r: SloForecastResult) -> SloForecastResultDict:
    m = r.metrics
    return {
        "serviceId": r.service_id,
        "windowKind": r.window_kind,
        "errorBudgetRemainingPct": r.error_budget_remaining_pct,
        "sloTargetAvailabilityPct": r.slo_target_availability_pct,
        "riskTier": r.risk_tier,
        "score": {"budget": r.score.budget, "velocity": r.score.velocity, "overall": r.score.overall},
        "metrics": {
            "totalEvents": m.total_events,
            "observedBadSharePct": m.observed_bad_share_pct,
            "maxBadSharePct": m.max_bad_share_pct,
            "burnMultiple": m.burn_multiple,
            "eventsPerHour": m.events_per_hour,
            "badEventsPerHour": m.bad_events_per_hour,
            "sustainableBadEventsPerHour": m.sustainable_bad_events_per_hour,
            "projectedExhaustionHours": m.projected_exhaustion_hours,
        },
        "issues": [issue_to_dict(i) for i in r.issues],
        "recommendedActions": list(r.recommended_actions),
        "generatedAtISO": r.generated_at_iso,
    }


_REQUIRED = frozenset(
    {
        "serviceId",
        "sloTargetAvailabilityPct",
        "windowKind",
        "windowHours",
        "goodEvents",
        "badEvents",
        "errorBudgetRemainingPct",
    }
)

_WINDOW_KINDS = frozenset({"1h", "6h", "24h", "7d", "30d"})


def parse_forecast_from_json(data: Dict[str, Any]) -> SloForecastInput:
    missing = [k for k in _REQUIRED if k not in data]
    if missing:
        raise ValueError(f"Missing fields: {', '.join(sorted(missing))}")

    wk = data["windowKind"]
    if wk not in _WINDOW_KINDS:
        raise ValueError(f"Invalid windowKind: {wk!r}")

    return SloForecastInput(
        service_id=str(data["serviceId"]),
        slo_target_availability_pct=float(data["sloTargetAvailabilityPct"]),
        window_kind=wk,  # type: ignore[arg-type]
        window_hours=float(data["windowHours"]),
        good_events=int(data["goodEvents"]),
        bad_events=int(data["badEvents"]),
        error_budget_remaining_pct=float(data["errorBudgetRemainingPct"]),
    )
