from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Iterable

from course.planner.constants import DEFAULT_LEARNING_MODULES, DEFAULT_MILESTONES
from course.planner.types import (
    LearningModule,
    LearningPlan,
    PlannedSession,
    PlannerExecutionResult,
    PlannerSummary,
    PlannerUserProfile,
)

DIFFICULTY_WEIGHT = {"beginner": 1, "intermediate": 2, "advanced": 3}
SESSION_WEIGHT = {"recorded": 1, "live": 2, "project": 3, "assessment": 2}
PREFERENCE_BOOST = {
    "short-sessions": -10,
    "deep-work": 20,
    "weekend-focus": 15,
    "daily-practice": 5,
}
GOAL_TAGS = {
    "job-switch": ["project", "testing", "portfolio"],
    "promotion": ["architecture", "review", "leadership"],
    "skill-refresh": ["refactor", "quality", "types"],
    "exam-prep": ["assessment", "logic", "coverage"],
    "portfolio-build": ["portfolio", "deployment", "review"],
}


def minutes_from_hours(hours: int | float) -> int:
    return round(float(hours) * 60)


def get_weekly_capacity_minutes(profile: PlannerUserProfile) -> int:
    base_minutes = minutes_from_hours(profile["weekly_hours"])
    boost = PREFERENCE_BOOST[profile["preference"]]
    return max(90, base_minutes + boost)


def validate_inputs(profile: PlannerUserProfile, modules: list[LearningModule], include_assessment: bool) -> list[str]:
    errors: list[str] = []

    if profile["weekly_hours"] < 2:
        errors.append("Weekly hours should be at least 2.")

    if not profile["active_days"]:
        errors.append("At least one active day is required.")

    if profile["target_level"] == "beginner" and profile["current_level"] == "advanced":
        errors.append("Target level should not be lower than current level.")

    if not modules:
        errors.append("At least one module is required.")
        return errors

    module_ids: set[str] = set()
    for module in modules:
        module_id = module["id"]
        if module_id in module_ids:
            errors.append(f"Duplicate module id detected: {module_id}")
        module_ids.add(module_id)

        if module["estimated_hours"] <= 0:
            errors.append(f"Module {module_id} should have positive estimated_hours.")

        if not include_assessment and module["session_type"] == "assessment" and module["required"]:
            errors.append(f"Module {module_id} is required assessment while include_assessment is false.")

    for module in modules:
        for prerequisite in module["prerequisites"]:
            if prerequisite not in module_ids:
                errors.append(f"Module {module['id']} has unknown prerequisite {prerequisite}")

    return errors


def order_modules_by_prerequisites(modules: list[LearningModule]) -> list[LearningModule]:
    module_map = {module["id"]: module for module in modules}
    visiting: set[str] = set()
    visited: set[str] = set()
    ordered: list[LearningModule] = []

    def dfs(module_id: str) -> None:
        if module_id in visited:
            return
        if module_id in visiting:
            raise ValueError(f"Circular dependency detected at {module_id}")

        module = module_map.get(module_id)
        if not module:
            return

        visiting.add(module_id)
        for prerequisite in module["prerequisites"]:
            dfs(prerequisite)

        visiting.remove(module_id)
        visited.add(module_id)
        ordered.append(module)

    for module in modules:
        dfs(module["id"])

    return ordered


def pick_focus_modules(profile: PlannerUserProfile, modules: list[LearningModule]) -> list[str]:
    desired_tags = set(GOAL_TAGS[profile["goal"]])

    scored: list[tuple[str, int]] = []
    for module in modules:
        score = 0

        if module["required"]:
            score += 9
        else:
            score += 2

        if DIFFICULTY_WEIGHT[module["difficulty"]] >= DIFFICULTY_WEIGHT[profile["current_level"]]:
            score += DIFFICULTY_WEIGHT[module["difficulty"]] * 4
        else:
            score += 1

        score += SESSION_WEIGHT[module["session_type"]] * 2

        matching_tags = desired_tags.intersection(module["tags"])
        score += len(matching_tags) * 4

        scored.append((module["id"], score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [module_id for module_id, _ in scored[:4]]


def _build_session_id(plan_id: str, index: int) -> str:
    return f"{plan_id}-S{index + 1:03d}"


def _pick_modules(modules: list[LearningModule], include_assessment: bool) -> list[LearningModule]:
    selected: list[LearningModule] = []
    for module in modules:
        if not include_assessment and module["session_type"] == "assessment":
            continue

        if module["required"] or module["difficulty"] != "advanced":
            selected.append(module)

    return selected


def _compute_status(coverage_score: int, warnings: list[str]) -> str:
    if warnings:
        return "overloaded"
    if coverage_score >= 90:
        return "ready"
    if coverage_score >= 70:
        return "rebalanced"
    return "draft"


def compute_coverage_score(profile: PlannerUserProfile, modules: list[LearningModule], sessions: list[PlannedSession]) -> int:
    required_module_ids = {module["id"] for module in modules if module["required"]}
    planned_module_ids = {session["module_id"] for session in sessions}

    covered_required = len(required_module_ids.intersection(planned_module_ids))
    required_coverage = int((covered_required / len(required_module_ids)) * 100) if required_module_ids else 100

    scheduled_types = {session["session_type"] for session in sessions}
    modality_bonus = 10 if {"recorded", "live", "project"}.issubset(scheduled_types) else 0

    all_tags = set(tag for module in modules for tag in module["tags"])
    goal_alignment = len(set(GOAL_TAGS[profile["goal"]]).intersection(all_tags))
    goal_bonus = min(10, goal_alignment * 3)

    return min(100, required_coverage + modality_bonus + goal_bonus)


def build_plan(
    profile: PlannerUserProfile,
    modules: list[LearningModule],
    include_assessment: bool = True,
    start_week: int = 1,
    max_weeks: int = 14,
) -> LearningPlan:
    ordered = order_modules_by_prerequisites(modules)
    selected_modules = _pick_modules(ordered, include_assessment)
    weekly_capacity = get_weekly_capacity_minutes(profile)

    plan_id = f"LP-{profile['user_id']}-{int(datetime.utcnow().timestamp()) % 1000000}"

    sessions: list[PlannedSession] = []
    warnings: list[str] = []
    current_week = start_week
    week_minutes = 0
    day_index = 0

    for module_index, module in enumerate(selected_modules):
        total_minutes = minutes_from_hours(module["estimated_hours"])
        slices = max(1, -(-total_minutes // 90))
        slice_minutes = -(-total_minutes // slices)

        for slice_index in range(slices):
            planned_minutes = min(slice_minutes, total_minutes - slice_index * slice_minutes)

            if week_minutes + planned_minutes > weekly_capacity:
                current_week += 1
                week_minutes = 0
                day_index = 0

            if current_week - start_week + 1 > max_weeks:
                warnings.append(f"Plan exceeded max weeks while scheduling module {module['id']}")

            day = profile["active_days"][day_index % len(profile["active_days"])]
            day_index += 1
            week_minutes += planned_minutes

            milestone_level = module["difficulty"]
            milestone_list = DEFAULT_MILESTONES[milestone_level]
            milestone = milestone_list[(module_index + slice_index) % len(milestone_list)]

            sessions.append(
                {
                    "session_id": _build_session_id(plan_id, len(sessions)),
                    "module_id": module["id"],
                    "title": f"{module['title']} - Part {slice_index + 1}",
                    "week_number": current_week,
                    "day": day,
                    "planned_minutes": planned_minutes,
                    "session_type": module["session_type"],
                    "milestone": milestone,
                }
            )

    total_minutes = sum(session["planned_minutes"] for session in sessions)
    coverage_score = compute_coverage_score(profile, modules, sessions)

    return {
        "plan_id": plan_id,
        "user_id": profile["user_id"],
        "status": _compute_status(coverage_score, warnings),
        "total_weeks": max(1, current_week - start_week + 1),
        "total_planned_minutes": total_minutes,
        "coverage_score": coverage_score,
        "warnings": warnings,
        "sessions": sessions,
        "focus_modules": pick_focus_modules(profile, selected_modules),
    }


def _week_loads(sessions: Iterable[PlannedSession]) -> dict[int, int]:
    loads: dict[int, int] = defaultdict(int)
    for session in sessions:
        loads[session["week_number"]] += session["planned_minutes"]
    return dict(loads)


def rebalance_plan(plan: LearningPlan, weekly_capacity: int) -> LearningPlan:
    copied_sessions: list[PlannedSession] = [dict(session) for session in plan["sessions"]]
    loads = _week_loads(copied_sessions)

    overloaded_weeks = [week for week, minutes in loads.items() if minutes > weekly_capacity]
    if not overloaded_weeks:
        cloned = dict(plan)
        cloned["status"] = "rebalanced" if plan["status"] == "overloaded" else plan["status"]
        return cloned

    warnings = list(plan["warnings"])

    for week in overloaded_weeks:
        overflow = loads[week] - weekly_capacity
        week_sessions = sorted(
            [session for session in copied_sessions if session["week_number"] == week],
            key=lambda session: session["planned_minutes"],
            reverse=True,
        )

        move_index = 0
        while overflow > 0 and move_index < len(week_sessions):
            target = week_sessions[move_index]
            movable = max(0, target["planned_minutes"] // 2)
            move_minutes = min(overflow, movable)

            if move_minutes < 20:
                move_index += 1
                continue

            target["planned_minutes"] -= move_minutes
            copied_sessions.append(
                {
                    "session_id": f"{target['session_id']}-R{move_index + 1}",
                    "module_id": target["module_id"],
                    "title": f"{target['title']} (Rebalanced)",
                    "week_number": target["week_number"] + 1,
                    "day": target["day"],
                    "planned_minutes": move_minutes,
                    "session_type": target["session_type"],
                    "milestone": target["milestone"],
                }
            )

            loads[week] -= move_minutes
            loads[target["week_number"] + 1] = loads.get(target["week_number"] + 1, 0) + move_minutes
            overflow -= move_minutes
            move_index += 1

        if overflow > 0:
            warnings.append(f"Week {week} remains overloaded by {overflow} minutes after rebalance")

    copied_sessions.sort(key=lambda session: (session["week_number"], session["session_id"]))

    new_plan = dict(plan)
    new_plan["sessions"] = copied_sessions
    new_plan["total_weeks"] = max(session["week_number"] for session in copied_sessions)
    new_plan["total_planned_minutes"] = sum(session["planned_minutes"] for session in copied_sessions)
    new_plan["warnings"] = warnings
    new_plan["status"] = "overloaded" if warnings else "rebalanced"
    return new_plan


def build_summary(modules: list[LearningModule], plan: LearningPlan) -> PlannerSummary:
    required_count = len([module for module in modules if module["required"]])
    optional_count = len(modules) - required_count

    week_loads = _week_loads(plan["sessions"])
    average_load = (plan["total_planned_minutes"] / plan["total_weeks"]) if plan["total_weeks"] else 0
    heavy_weeks = [week for week, minutes in week_loads.items() if minutes > average_load * 1.2]

    return {
        "total_modules": len(modules),
        "required_modules": required_count,
        "optional_modules": optional_count,
        "total_estimated_minutes": sum(minutes_from_hours(module["estimated_hours"]) for module in modules),
        "heavy_weeks": sorted(heavy_weeks),
    }


def run_planner(
    profile: PlannerUserProfile,
    include_assessment: bool,
    max_weeks: int,
    start_week: int,
    modules: list[LearningModule] | None = None,
    rebalance_overload: bool = True,
) -> PlannerExecutionResult:
    selected_modules = modules or DEFAULT_LEARNING_MODULES
    validation_errors = validate_inputs(profile, selected_modules, include_assessment)

    if validation_errors:
        return {
            "plan": {
                "plan_id": f"LP-{profile['user_id']}-invalid",
                "user_id": profile["user_id"],
                "status": "draft",
                "total_weeks": 0,
                "total_planned_minutes": 0,
                "coverage_score": 0,
                "warnings": validation_errors,
                "sessions": [],
                "focus_modules": [],
            },
            "summary": {
                "total_modules": len(selected_modules),
                "required_modules": 0,
                "optional_modules": 0,
                "total_estimated_minutes": 0,
                "heavy_weeks": [],
            },
            "validation_errors": validation_errors,
        }

    draft_plan = build_plan(
        profile=profile,
        modules=selected_modules,
        include_assessment=include_assessment,
        start_week=start_week,
        max_weeks=max_weeks,
    )

    final_plan = draft_plan
    if rebalance_overload:
        final_plan = rebalance_plan(draft_plan, get_weekly_capacity_minutes(profile))

    summary = build_summary(selected_modules, final_plan)

    return {
        "plan": final_plan,
        "summary": summary,
        "validation_errors": [],
    }
