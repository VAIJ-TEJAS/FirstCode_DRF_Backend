from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient


class PlannerApiP2PTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="planner-flow", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_p2p_006_full_planner_request_returns_plan_and_summary(self):
        response = self.client.post(
            "/learning-path/planner/",
            {
                "current_level": "beginner",
                "target_level": "advanced",
                "weekly_hours": 8,
                "goal": "job-switch",
                "preference": "daily-practice",
                "active_days": ["monday", "tuesday", "thursday", "saturday"],
                "include_assessment": True,
                "max_weeks": 16,
                "start_week": 1,
                "rebalance_overload": True,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["validation_errors"], [])
        self.assertGreater(len(response.data["plan"]["sessions"]), 0)
        self.assertGreater(response.data["summary"]["total_modules"], 0)

    def test_p2p_007_assessment_toggle_changes_plan_output(self):
        with_assessment = self.client.post(
            "/learning-path/planner/",
            {
                "include_assessment": True,
                "weekly_hours": 8,
                "active_days": ["monday", "wednesday", "friday"],
                "goal": "job-switch",
            },
            format="json",
        )

        without_assessment = self.client.post(
            "/learning-path/planner/",
            {
                "include_assessment": False,
                "weekly_hours": 8,
                "active_days": ["monday", "wednesday", "friday"],
                "goal": "job-switch",
            },
            format="json",
        )

        self.assertEqual(with_assessment.status_code, 200)
        self.assertEqual(without_assessment.status_code, 200)

        has_assessment = any(
            session["session_type"] == "assessment"
            for session in with_assessment.data["plan"]["sessions"]
        )
        has_assessment_disabled = any(
            session["session_type"] == "assessment"
            for session in without_assessment.data["plan"]["sessions"]
        )

        self.assertTrue(has_assessment)
        self.assertFalse(has_assessment_disabled)

    def test_p2p_008_limited_weeks_adds_warnings_for_overflow(self):
        response = self.client.post(
            "/learning-path/planner/",
            {
                "weekly_hours": 2,
                "active_days": ["monday"],
                "max_weeks": 2,
                "start_week": 1,
                "goal": "portfolio-build",
                "preference": "short-sessions",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        warnings = response.data["plan"]["warnings"]
        self.assertTrue(any("Plan exceeded max weeks" in warning for warning in warnings))

    def test_p2p_009_rebalance_switch_affects_generated_session_count(self):
        with_rebalance = self.client.post(
            "/learning-path/planner/",
            {
                "weekly_hours": 3,
                "active_days": ["monday", "thursday"],
                "rebalance_overload": True,
                "goal": "job-switch",
            },
            format="json",
        )
        without_rebalance = self.client.post(
            "/learning-path/planner/",
            {
                "weekly_hours": 3,
                "active_days": ["monday", "thursday"],
                "rebalance_overload": False,
                "goal": "job-switch",
            },
            format="json",
        )

        self.assertEqual(with_rebalance.status_code, 200)
        self.assertEqual(without_rebalance.status_code, 200)
        self.assertGreaterEqual(
            len(with_rebalance.data["plan"]["sessions"]),
            len(without_rebalance.data["plan"]["sessions"]),
        )
