from django.test import SimpleTestCase

from course.planner.constants import DEFAULT_LEARNING_MODULES
from course.planner.engine import build_plan, build_summary, get_weekly_capacity_minutes, rebalance_plan, run_planner


class PlannerEngineP2PTests(SimpleTestCase):
    def setUp(self):
        self.profile = {
            "user_id": 42,
            "current_level": "beginner",
            "target_level": "advanced",
            "weekly_hours": 7,
            "goal": "job-switch",
            "preference": "daily-practice",
            "active_days": ["monday", "wednesday", "friday", "saturday"],
        }

    def test_p2p_001_run_planner_returns_ready_journey_with_valid_inputs(self):
        result = run_planner(
            profile=self.profile,
            include_assessment=True,
            max_weeks=18,
            start_week=1,
            rebalance_overload=True,
        )

        self.assertEqual(result["validation_errors"], [])
        self.assertGreater(len(result["plan"]["sessions"]), 0)
        self.assertIn(result["plan"]["status"], ["ready", "rebalanced", "overloaded"])
        self.assertGreaterEqual(result["plan"]["coverage_score"], 80)
        self.assertGreater(result["summary"]["total_modules"], 0)

    def test_p2p_002_run_planner_returns_draft_for_invalid_profile(self):
        invalid_profile = {
            **self.profile,
            "weekly_hours": 1,
            "active_days": [],
        }

        result = run_planner(
            profile=invalid_profile,
            include_assessment=True,
            max_weeks=10,
            start_week=1,
            rebalance_overload=True,
        )

        self.assertEqual(result["plan"]["status"], "draft")
        self.assertEqual(result["plan"]["sessions"], [])
        self.assertGreaterEqual(len(result["validation_errors"]), 2)

    def test_p2p_003_rebalance_plan_splits_overloaded_week(self):
        constrained_profile = {
            **self.profile,
            "weekly_hours": 3,
            "active_days": ["monday", "thursday"],
        }

        draft_plan = build_plan(
            profile=constrained_profile,
            modules=DEFAULT_LEARNING_MODULES,
            include_assessment=True,
            start_week=1,
            max_weeks=20,
        )
        capacity = get_weekly_capacity_minutes(constrained_profile)
        rebalanced = rebalance_plan(draft_plan, capacity)

        self.assertGreaterEqual(len(rebalanced["sessions"]), len(draft_plan["sessions"]))
        split_sessions = [session for session in rebalanced["sessions"] if "-R" in session["session_id"]]
        self.assertGreaterEqual(len(split_sessions), 1)

    def test_p2p_004_build_summary_consistency_after_plan_generation(self):
        draft_plan = build_plan(
            profile={**self.profile, "weekly_hours": 5, "active_days": ["saturday"]},
            modules=DEFAULT_LEARNING_MODULES,
            include_assessment=False,
            start_week=2,
            max_weeks=14,
        )

        summary = build_summary(DEFAULT_LEARNING_MODULES, draft_plan)

        self.assertEqual(summary["total_modules"], len(DEFAULT_LEARNING_MODULES))
        self.assertEqual(
            summary["required_modules"] + summary["optional_modules"],
            summary["total_modules"],
        )
        self.assertGreater(summary["total_estimated_minutes"], 0)

    def test_p2p_005_include_assessment_false_removes_assessment_sessions(self):
        result = run_planner(
            profile=self.profile,
            include_assessment=False,
            max_weeks=16,
            start_week=1,
            rebalance_overload=True,
        )

        self.assertEqual(result["validation_errors"], [])
        has_assessment = any(session["session_type"] == "assessment" for session in result["plan"]["sessions"])
        self.assertFalse(has_assessment)
