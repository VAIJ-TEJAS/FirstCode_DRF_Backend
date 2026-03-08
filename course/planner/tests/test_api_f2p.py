from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from course.planner.views import LearningPathPlannerAPIView


class PlannerApiF2PTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = LearningPathPlannerAPIView.as_view()
        self.user = User.objects.create_user(username="planner-user", password="password123")

    def test_f2p_009_api_rejects_missing_authentication(self):
        request = self.factory.post("/learning-path/planner/", {}, format="json")
        response = self.view(request)

        self.assertEqual(response.status_code, 401)

    def test_f2p_010_api_rejects_invalid_weekly_hours(self):
        request = self.factory.post(
            "/learning-path/planner/",
            {
                "weekly_hours": 1,
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = self.view(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("weekly_hours", response.data)

    def test_f2p_011_api_applies_defaults_for_optional_fields(self):
        request = self.factory.post(
            "/learning-path/planner/",
            {
                "goal": "job-switch",
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = self.view(request)

        self.assertEqual(response.status_code, 200)
        self.assertIn("plan", response.data)
        self.assertIn("summary", response.data)
        self.assertEqual(response.data["plan"]["user_id"], self.user.id)

    def test_f2p_012_api_rejects_invalid_active_days_value(self):
        request = self.factory.post(
            "/learning-path/planner/",
            {
                "active_days": ["monday", "funday"],
            },
            format="json",
        )
        force_authenticate(request, user=self.user)

        response = self.view(request)

        self.assertEqual(response.status_code, 400)
        self.assertIn("active_days", response.data)
