from __future__ import annotations

import os
from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction


@dataclass(frozen=True)
class DemoCredentials:
    admin_username: str
    admin_password: str
    admin_email: str
    demo_username: str
    demo_password: str
    demo_email: str


def _get_credentials() -> DemoCredentials:
    """
    Seed credentials are configurable via env so Docker can keep them consistent.
    """

    return DemoCredentials(
        admin_username=os.getenv("DEMO_ADMIN_USERNAME", os.getenv("DJANGO_SUPERUSER_USERNAME", "admin")),
        admin_password=os.getenv("DEMO_ADMIN_PASSWORD", os.getenv("DJANGO_SUPERUSER_PASSWORD", "Admin@12345")),
        admin_email=os.getenv("DEMO_ADMIN_EMAIL", os.getenv("DJANGO_SUPERUSER_EMAIL", "admin@example.com")),
        demo_username=os.getenv("DEMO_USER_USERNAME", "demo"),
        demo_password=os.getenv("DEMO_USER_PASSWORD", "Demo@12345"),
        demo_email=os.getenv("DEMO_USER_EMAIL", "demo@example.com"),
    )


class Command(BaseCommand):
    help = "Seed a minimal demo dataset (users + sample courses) for local/docker skimming."

    @transaction.atomic
    def handle(self, *args, **kwargs):
        creds = _get_credentials()

        User = get_user_model()

        admin, created_admin = User.objects.get_or_create(
            username=creds.admin_username,
            defaults={"email": creds.admin_email},
        )
        if created_admin:
            admin.is_staff = True
            admin.is_superuser = True
            admin.set_password(creds.admin_password)
            admin.save(update_fields=["email", "is_staff", "is_superuser", "password"])
            self.stdout.write(self.style.SUCCESS(f"Created admin user: {creds.admin_username}"))
        else:
            # Ensure it's usable even if it existed
            changed = False
            if not admin.is_staff:
                admin.is_staff = True
                changed = True
            if not admin.is_superuser:
                admin.is_superuser = True
                changed = True
            if admin.email != creds.admin_email and creds.admin_email:
                admin.email = creds.admin_email
                changed = True
            if changed:
                admin.save()
            self.stdout.write(self.style.WARNING(f"Admin user already exists: {creds.admin_username}"))

        demo_user, created_demo = User.objects.get_or_create(
            username=creds.demo_username,
            defaults={"email": creds.demo_email},
        )
        if created_demo:
            demo_user.set_password(creds.demo_password)
            demo_user.save(update_fields=["email", "password"])
            self.stdout.write(self.style.SUCCESS(f"Created demo user: {creds.demo_username}"))
        else:
            self.stdout.write(self.style.WARNING(f"Demo user already exists: {creds.demo_username}"))

        self._seed_course_data(demo_user)

        self.stdout.write(self.style.SUCCESS("Demo seed complete."))

    def _seed_course_data(self, demo_user):
        """
        Create a small, realistic content tree so the UI/admin has something to show.
        The models live in `course` and `user`.
        """

        from course.models import Category, Chapter, Course, Lesson, Tag, Task, Track, UserCourse
        from user.models import Pattern

        pattern, _ = Pattern.objects.get_or_create(
            code="FC-STD",
            defaults={
                "name": "Standard Track",
                "description": "Default learning pattern for demo content.",
            },
        )

        cat_prof, _ = Category.objects.get_or_create(
            name="Professional",
            defaults={"description": "Career-focused learning tracks."},
        )
        cat_personal, _ = Category.objects.get_or_create(
            name="Personal",
            defaults={"description": "Personal productivity and enrichment."},
        )

        tag_python, _ = Tag.objects.get_or_create(
            name="python",
            defaults={"description": "Python fundamentals and applied practice."},
        )
        tag_backend, _ = Tag.objects.get_or_create(
            name="backend",
            defaults={"description": "Backend engineering."},
        )
        tag_frontend, _ = Tag.objects.get_or_create(
            name="frontend",
            defaults={"description": "Frontend engineering."},
        )

        courses = [
            {
                "category": cat_prof,
                "main_category": "Professional",
                "name": "Backend Foundations",
                "short_description": "APIs, data modeling, and practical Django fundamentals.",
                "long_description": "A hands-on course that walks through building and operating a small web API. Includes patterns for validation, testing, and safe deployments.",
                "requirements": "Basic Python familiarity. No prior Django required.",
                "is_paid": False,
                "tags": [tag_python, tag_backend],
            },
            {
                "category": cat_prof,
                "main_category": "Professional",
                "name": "Frontend for Busy Engineers",
                "short_description": "Practical UI patterns with a focus on readability and shipping.",
                "long_description": "Covers component design, state management, and production checks. Includes realistic examples and integration points.",
                "requirements": "Basic JavaScript familiarity.",
                "is_paid": False,
                "tags": [tag_frontend],
            },
            {
                "category": cat_personal,
                "main_category": "Personal",
                "name": "Deep Work Toolkit",
                "short_description": "A lightweight program to improve focus and execution.",
                "long_description": "A short program with experiments and a weekly routine you can adapt. Focuses on structure, review loops, and sustainable habits.",
                "requirements": "None.",
                "is_paid": True,
                "tags": [],
            },
        ]

        created_courses = []

        for spec in courses:
            course, _ = Course.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "category": spec["category"],
                    "main_category": spec["main_category"],
                    "short_description": spec["short_description"],
                    "long_description": spec["long_description"],
                    "requirements": spec["requirements"],
                    "is_paid": spec["is_paid"],
                },
            )
            # Keep fields up to date if content changes over time
            if course.category_id != spec["category"].id:
                course.category = spec["category"]
            course.main_category = spec["main_category"]
            course.short_description = spec["short_description"]
            course.long_description = spec["long_description"]
            course.requirements = spec["requirements"]
            course.is_paid = spec["is_paid"]
            course.save()

            if spec["tags"]:
                course.tags.set(spec["tags"])
            created_courses.append(course)

        # Build a minimal content tree for the first course
        primary = created_courses[0]
        track, _ = Track.objects.get_or_create(
            course=primary,
            pattern=pattern,
            name="Core Track",
            defaults={"description": "A compact, skimmable track of foundational lessons."},
        )
        if not track.description:
            track.description = "A compact, skimmable track of foundational lessons."
            track.save(update_fields=["description"])

        chapter, _ = Chapter.objects.get_or_create(
            track=track,
            order=1,
            name="Getting Started",
            defaults={"description": "Project setup, API basics, and sanity checks."},
        )

        lesson1, _ = Lesson.objects.get_or_create(
            chapter=chapter,
            order=1,
            name="Project overview",
            defaults={
                "short_description": "How the pieces fit together.",
                "long_description": "You’ll skim the architecture and the request flow, then validate with a few quick checks.",
                "requirements": "None.",
                "playground_type": "Python",
                "quote": "Small steps, tight feedback loops.",
            },
        )

        lesson2, _ = Lesson.objects.get_or_create(
            chapter=chapter,
            order=2,
            name="Running locally and in Docker",
            defaults={
                "short_description": "Start services and verify core endpoints.",
                "long_description": "You’ll run migrations, seed demo data, and confirm the API is responding. This lesson is intentionally hands-on.",
                "requirements": "Docker Desktop installed.",
                "playground_type": "Python",
            },
        )

        Task.objects.get_or_create(
            lesson=lesson1,
            name="Skim the API surface",
            defaults={"description": "<p>Open the API views and identify 3 endpoints you want to verify.</p>"},
        )
        Task.objects.get_or_create(
            lesson=lesson2,
            name="Start the stack",
            defaults={"description": "<p>Run docker compose up and confirm you can log into /admin.</p>"},
        )

        UserCourse.objects.get_or_create(
            user=demo_user,
            course=primary,
            defaults={
                "completed_chapters": 0,
                "progress": 12.50,
                "status": "In Progress",
            },
        )

