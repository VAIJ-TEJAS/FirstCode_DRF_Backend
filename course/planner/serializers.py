from rest_framework import serializers

from course.planner.constants import DEFAULT_ACTIVE_DAYS


class PlannerRequestSerializer(serializers.Serializer):
    current_level = serializers.ChoiceField(choices=["beginner", "intermediate", "advanced"], required=False)
    target_level = serializers.ChoiceField(choices=["beginner", "intermediate", "advanced"], required=False)
    weekly_hours = serializers.IntegerField(min_value=2, max_value=60, required=False)
    goal = serializers.ChoiceField(
        choices=["job-switch", "promotion", "skill-refresh", "exam-prep", "portfolio-build"],
        required=False,
    )
    preference = serializers.ChoiceField(
        choices=["short-sessions", "deep-work", "weekend-focus", "daily-practice"],
        required=False,
    )
    active_days = serializers.ListField(
        child=serializers.ChoiceField(
            choices=["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        ),
        required=False,
        allow_empty=False,
    )
    include_assessment = serializers.BooleanField(required=False)
    max_weeks = serializers.IntegerField(min_value=2, max_value=52, required=False)
    start_week = serializers.IntegerField(min_value=1, max_value=52, required=False)
    rebalance_overload = serializers.BooleanField(required=False)

    def to_internal_value(self, data):
        internal = super().to_internal_value(data)

        defaults = {
            "current_level": "beginner",
            "target_level": "advanced",
            "weekly_hours": 8,
            "goal": "job-switch",
            "preference": "daily-practice",
            "active_days": list(DEFAULT_ACTIVE_DAYS),
            "include_assessment": True,
            "max_weeks": 14,
            "start_week": 1,
            "rebalance_overload": True,
        }

        for key, value in defaults.items():
            internal.setdefault(key, value)

        return internal


class PlannerSessionSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    module_id = serializers.CharField()
    title = serializers.CharField()
    week_number = serializers.IntegerField()
    day = serializers.CharField()
    planned_minutes = serializers.IntegerField()
    session_type = serializers.CharField()
    milestone = serializers.CharField()


class PlannerPlanSerializer(serializers.Serializer):
    plan_id = serializers.CharField()
    user_id = serializers.IntegerField()
    status = serializers.CharField()
    total_weeks = serializers.IntegerField()
    total_planned_minutes = serializers.IntegerField()
    coverage_score = serializers.IntegerField()
    warnings = serializers.ListField(child=serializers.CharField())
    sessions = PlannerSessionSerializer(many=True)
    focus_modules = serializers.ListField(child=serializers.CharField())


class PlannerSummarySerializer(serializers.Serializer):
    total_modules = serializers.IntegerField()
    required_modules = serializers.IntegerField()
    optional_modules = serializers.IntegerField()
    total_estimated_minutes = serializers.IntegerField()
    heavy_weeks = serializers.ListField(child=serializers.IntegerField())


class PlannerResponseSerializer(serializers.Serializer):
    plan = PlannerPlanSerializer()
    summary = PlannerSummarySerializer()
    validation_errors = serializers.ListField(child=serializers.CharField())
