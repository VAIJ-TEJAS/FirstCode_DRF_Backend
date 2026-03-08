from django.test import SimpleTestCase

from course.planner.constants import DEFAULT_LEARNING_MODULES
from course.planner.engine import (
    compute_coverage_score,
    get_weekly_capacity_minutes,
    order_modules_by_prerequisites,
    pick_focus_modules,
    validate_inputs,
)


class PlannerEngineF2PTests(SimpleTestCase):
    def setUp(self):
        self.profile = {
            "user_id": 11,
            "current_level": "beginner",
            "target_level": "advanced",
            "weekly_hours": 8,
            "goal": "job-switch",
            "preference": "daily-practice",
            "active_days": ["monday", "tuesday", "thursday", "saturday"],
        }

    def test_f2p_001_validate_inputs_success(self):
        errors = validate_inputs(self.profile, DEFAULT_LEARNING_MODULES, include_assessment=True)
        self.assertEqual(errors, [])

    def test_f2p_002_validate_inputs_rejects_small_weekly_hours(self):
        profile = {**self.profile, "weekly_hours": 1}
        errors = validate_inputs(profile, DEFAULT_LEARNING_MODULES, include_assessment=True)

        self.assertIn("Weekly hours should be at least 2.", errors)

    def test_f2p_003_validate_inputs_rejects_empty_days(self):
        profile = {**self.profile, "active_days": []}
        errors = validate_inputs(profile, DEFAULT_LEARNING_MODULES, include_assessment=True)

        self.assertIn("At least one active day is required.", errors)

    def test_f2p_004_validate_inputs_detects_unknown_prerequisite(self):
        broken = [*DEFAULT_LEARNING_MODULES]
        broken.append(
            {
                "id": "broken-module",
                "title": "Broken",
                "domain": "frontend",
                "difficulty": "beginner",
                "estimated_hours": 3,
                "session_type": "recorded",
                "required": False,
                "prerequisites": ["missing-module"],
                "tags": ["broken"],
            }
        )

        errors = validate_inputs(self.profile, broken, include_assessment=True)
        self.assertTrue(any("missing-module" in error for error in errors))

    def test_f2p_005_weekly_capacity_changes_with_preference(self):
        short = get_weekly_capacity_minutes({**self.profile, "weekly_hours": 5, "preference": "short-sessions"})
        deep = get_weekly_capacity_minutes({**self.profile, "weekly_hours": 5, "preference": "deep-work"})

        self.assertEqual(short, 290)
        self.assertEqual(deep, 320)
        self.assertGreater(deep, short)

    def test_f2p_006_order_modules_keeps_dependencies(self):
        ordered = order_modules_by_prerequisites(DEFAULT_LEARNING_MODULES)
        ids = [module["id"] for module in ordered]

        self.assertLess(ids.index("module-html-css"), ids.index("module-js-basics"))
        self.assertLess(ids.index("module-js-basics"), ids.index("module-react-core"))
        self.assertLess(ids.index("module-react-core"), ids.index("module-nextjs"))

    def test_f2p_007_focus_modules_returns_top_four(self):
        focus = pick_focus_modules(self.profile, DEFAULT_LEARNING_MODULES)

        self.assertEqual(len(focus), 4)
        self.assertIn("module-capstone", focus)

    def test_f2p_008_coverage_score_high_for_rich_session_mix(self):
        sessions = [
            {
                "session_id": "S1",
                "module_id": "module-html-css",
                "title": "t1",
                "week_number": 1,
                "day": "monday",
                "planned_minutes": 90,
                "session_type": "recorded",
                "milestone": "a",
            },
            {
                "session_id": "S2",
                "module_id": "module-react-core",
                "title": "t2",
                "week_number": 1,
                "day": "tuesday",
                "planned_minutes": 90,
                "session_type": "live",
                "milestone": "b",
            },
            {
                "session_id": "S3",
                "module_id": "module-nextjs",
                "title": "t3",
                "week_number": 2,
                "day": "thursday",
                "planned_minutes": 90,
                "session_type": "project",
                "milestone": "c",
            },
            {
                "session_id": "S4",
                "module_id": "module-testing",
                "title": "t4",
                "week_number": 2,
                "day": "saturday",
                "planned_minutes": 90,
                "session_type": "assessment",
                "milestone": "d",
            },
            {
                "session_id": "S5",
                "module_id": "module-js-basics",
                "title": "t5",
                "week_number": 3,
                "day": "monday",
                "planned_minutes": 90,
                "session_type": "recorded",
                "milestone": "e",
            },
            {
                "session_id": "S6",
                "module_id": "module-typescript",
                "title": "t6",
                "week_number": 3,
                "day": "tuesday",
                "planned_minutes": 90,
                "session_type": "recorded",
                "milestone": "f",
            },
        ]

        score = compute_coverage_score(self.profile, DEFAULT_LEARNING_MODULES, sessions)
        self.assertGreaterEqual(score, 90)
