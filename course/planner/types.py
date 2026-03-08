from typing import Dict, List, Literal, TypedDict

DifficultyLevel = Literal["beginner", "intermediate", "advanced"]
SessionType = Literal["recorded", "live", "project", "assessment"]
UserGoal = Literal["job-switch", "promotion", "skill-refresh", "exam-prep", "portfolio-build"]
LearningPreference = Literal["short-sessions", "deep-work", "weekend-focus", "daily-practice"]
Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class PlannerUserProfile(TypedDict):
    user_id: int
    current_level: DifficultyLevel
    target_level: DifficultyLevel
    weekly_hours: int
    goal: UserGoal
    preference: LearningPreference
    active_days: List[Weekday]


class LearningModule(TypedDict):
    id: str
    title: str
    domain: str
    difficulty: DifficultyLevel
    estimated_hours: int
    session_type: SessionType
    required: bool
    prerequisites: List[str]
    tags: List[str]


class PlannedSession(TypedDict):
    session_id: str
    module_id: str
    title: str
    week_number: int
    day: Weekday
    planned_minutes: int
    session_type: SessionType
    milestone: str


class LearningPlan(TypedDict):
    plan_id: str
    user_id: int
    status: Literal["draft", "ready", "rebalanced", "overloaded"]
    total_weeks: int
    total_planned_minutes: int
    coverage_score: int
    warnings: List[str]
    sessions: List[PlannedSession]
    focus_modules: List[str]


class PlannerSummary(TypedDict):
    total_modules: int
    required_modules: int
    optional_modules: int
    total_estimated_minutes: int
    heavy_weeks: List[int]


class PlannerExecutionResult(TypedDict):
    plan: LearningPlan
    summary: PlannerSummary
    validation_errors: List[str]


MilestoneMap = Dict[DifficultyLevel, List[str]]
