from __future__ import annotations

import random
import string
from dataclasses import dataclass
from datetime import date, timedelta, time
from typing import Iterable, List, Sequence

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone


DEMO_PREFIX = "DEMO:"


@dataclass(frozen=True)
class SeedPlan:
    categories: int
    tags: int
    courses: int
    tracks_per_course: int
    chapters_per_track: int
    lessons_per_chapter: int
    tasks_per_lesson: int
    live_classes: int
    quotes: int
    enroll_courses: int
    enroll_live_classes: int


def _slug_token(n: int = 6) -> str:
    return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))


def _chunked(items: Sequence, size: int) -> Iterable[Sequence]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


class Command(BaseCommand):
    help = "Seed a large demo dataset for local/docker testing."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true", help="Delete previous DEMO: data before seeding.")
        parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic demo data.")

        parser.add_argument("--categories", type=int, default=12)
        parser.add_argument("--tags", type=int, default=40)
        parser.add_argument("--courses", type=int, default=120)
        parser.add_argument("--tracks-per-course", type=int, default=2)
        parser.add_argument("--chapters-per-track", type=int, default=4)
        parser.add_argument("--lessons-per-chapter", type=int, default=4)
        parser.add_argument("--tasks-per-lesson", type=int, default=2)
        parser.add_argument("--live-classes", type=int, default=30)
        parser.add_argument("--quotes", type=int, default=250)

        parser.add_argument("--enroll-courses", type=int, default=25)
        parser.add_argument("--enroll-live-classes", type=int, default=8)

        parser.add_argument("--demo-email", type=str, default="demo@example.com")

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(int(options["seed"]))

        plan = SeedPlan(
            categories=int(options["categories"]),
            tags=int(options["tags"]),
            courses=int(options["courses"]),
            tracks_per_course=int(options["tracks_per_course"]),
            chapters_per_track=int(options["chapters_per_track"]),
            lessons_per_chapter=int(options["lessons_per_chapter"]),
            tasks_per_lesson=int(options["tasks_per_lesson"]),
            live_classes=int(options["live_classes"]),
            quotes=int(options["quotes"]),
            enroll_courses=int(options["enroll_courses"]),
            enroll_live_classes=int(options["enroll_live_classes"]),
        )

        demo_email = str(options["demo_email"]).strip().lower()

        if options["reset"]:
            self._reset_demo_data()

        demo_user = self._get_demo_user(demo_email)
        self._ensure_subscription_and_profile(demo_user)

        categories = self._seed_categories(plan.categories)
        tags = self._seed_tags(plan.tags)
        courses = self._seed_courses(categories, tags, plan.courses)
        self._seed_course_tree(
            courses=courses,
            tracks_per_course=plan.tracks_per_course,
            chapters_per_track=plan.chapters_per_track,
            lessons_per_chapter=plan.lessons_per_chapter,
            tasks_per_lesson=plan.tasks_per_lesson,
        )
        self._seed_live_classes(plan.live_classes)
        self._seed_quotes(plan.quotes)
        self._seed_orders_for_user(demo_user)
        self._enroll_user(demo_user, courses, plan.enroll_courses, plan.enroll_live_classes)

        self.stdout.write(
            self.style.SUCCESS(
                f"Massive demo seed complete: {len(courses)} courses, {plan.live_classes} live classes."
            )
        )

    def _get_demo_user(self, email: str):
        User = get_user_model()
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            # Fallback: try username demo
            return User.objects.get(username="demo")

    def _ensure_subscription_and_profile(self, user):
        from subscription.models import Subscription, UserSubscription
        from user.models import Pattern, UserProfile

        pattern, _ = Pattern.objects.get_or_create(
            code="FC-MASS",
            defaults={
                "name": f"{DEMO_PREFIX} Massive Pattern",
                "description": "Pattern used for large demo dataset.",
            },
        )

        # Ensure a few subscription tiers exist
        tiers = [
            {"level": 0, "name": "Free", "price": 0, "validity": 365, "start_limit": 5, "enroll_limit": 5},
            {"level": 1, "name": "Pro", "price": 999, "validity": 365, "start_limit": 999, "enroll_limit": 999},
            {"level": 2, "name": "Enterprise", "price": 4999, "validity": 365, "start_limit": 9999, "enroll_limit": 9999},
        ]

        for tier in tiers:
            Subscription.objects.get_or_create(
                level=tier["level"],
                defaults={
                    "name": tier["name"],
                    "description": f"{tier['name']} tier",
                    "validity": tier["validity"],
                    "price": tier["price"],
                    "start_limit": tier["start_limit"],
                    "enroll_limit": tier["enroll_limit"],
                },
            )

        pro = Subscription.objects.get(level=1)
        now = timezone.now()
        current, _ = UserSubscription.objects.get_or_create(
            user=user,
            subscription=pro,
            status="Current",
            defaults={
                "subscription_start_date": now,
                "subscription_end_date": now + timedelta(days=pro.validity),
                "renewed": False,
                "payment": {"demo": True, "provider": "seed_massive"},
            },
        )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if profile.pattern_id != pattern.id:
            profile.pattern = pattern
        if profile.current_subscription_id != current.id:
            profile.current_subscription = current
        profile.save()

    def _reset_demo_data(self):
        from course.models import Category, Tag, Course, Track, Chapter, Lesson, Task, UserCourse
        from liveclass.models import LiveClass, UserLiveClass
        from quote.models import PersonalisedQuote
        from subscription.models import UserSubscription
        from user.models import Pattern, UserProfile
        from order.models import Order

        # Delete in a safe-ish order respecting FK cascades
        UserCourse.objects.filter(course__name__startswith=DEMO_PREFIX).delete()
        Task.objects.filter(lesson__chapter__track__course__name__startswith=DEMO_PREFIX).delete()
        Lesson.objects.filter(chapter__track__course__name__startswith=DEMO_PREFIX).delete()
        Chapter.objects.filter(track__course__name__startswith=DEMO_PREFIX).delete()
        Track.objects.filter(course__name__startswith=DEMO_PREFIX).delete()
        Course.objects.filter(name__startswith=DEMO_PREFIX).delete()

        LiveClass.objects.filter(name__startswith=DEMO_PREFIX).delete()
        UserLiveClass.objects.filter(live_class__name__startswith=DEMO_PREFIX).delete()

        Category.objects.filter(name__startswith=DEMO_PREFIX).delete()
        Tag.objects.filter(name__startswith=DEMO_PREFIX).delete()

        PersonalisedQuote.objects.filter(text__startswith=DEMO_PREFIX).delete()

        Order.objects.filter(order_id__startswith="DEMO-").delete()
        UserSubscription.objects.filter(payment__contains={"provider": "seed_massive"}).delete()
        UserProfile.objects.filter(pattern__code="FC-MASS").update(pattern=None)
        Pattern.objects.filter(code="FC-MASS").delete()

    def _seed_categories(self, count: int):
        from course.models import Category

        existing = Category.objects.filter(name__startswith=DEMO_PREFIX).count()
        if existing >= count:
            return list(Category.objects.filter(name__startswith=DEMO_PREFIX).order_by("id")[:count])

        to_create: List[Category] = []
        for i in range(existing, count):
            to_create.append(
                Category(
                    name=f"{DEMO_PREFIX} Category {i + 1:03d}",
                    description=f"Demo category {i + 1} for broad navigation coverage.",
                )
            )
        if to_create:
            Category.objects.bulk_create(to_create, batch_size=200)

        return list(Category.objects.filter(name__startswith=DEMO_PREFIX).order_by("id")[:count])

    def _seed_tags(self, count: int):
        from course.models import Tag

        existing = Tag.objects.filter(name__startswith=DEMO_PREFIX).count()
        if existing >= count:
            return list(Tag.objects.filter(name__startswith=DEMO_PREFIX).order_by("id")[:count])

        to_create: List[Tag] = []
        for i in range(existing, count):
            to_create.append(
                Tag(
                    name=f"{DEMO_PREFIX} tag-{i + 1:03d}",
                    description=f"Demo tag {i + 1}",
                )
            )
        if to_create:
            Tag.objects.bulk_create(to_create, batch_size=500)

        return list(Tag.objects.filter(name__startswith=DEMO_PREFIX).order_by("id")[:count])

    def _seed_courses(self, categories, tags, count: int):
        from course.models import Course

        existing = Course.objects.filter(name__startswith=DEMO_PREFIX).count()
        if existing < count:
            to_create: List[Course] = []
            for i in range(existing, count):
                cat = categories[i % len(categories)]
                main_category = "Professional" if i % 3 else "Personal"
                is_paid = (i % 5) == 0
                to_create.append(
                    Course(
                        category=cat,
                        main_category=main_category,
                        name=f"{DEMO_PREFIX} Course {i + 1:04d} {_slug_token(4)}",
                        short_description=f"High-volume demo course {i + 1}.",
                        long_description="A longer description used to test detail pages, truncation, and layout under content load.",
                        requirements="Basic computer literacy. This is demo content.",
                        is_paid=is_paid,
                    )
                )
            Course.objects.bulk_create(to_create, batch_size=200)

        courses = list(Course.objects.filter(name__startswith=DEMO_PREFIX).order_by("id")[:count])

        # Tags M2M via through table (fast)
        through = Course.tags.through
        existing_links = set(
            through.objects.filter(course_id__in=[c.id for c in courses]).values_list("course_id", "tag_id")
        )

        link_rows = []
        for idx, course in enumerate(courses):
            # assign 3-6 tags per course
            tag_count = 3 + (idx % 4)
            for tag in random.sample(tags, k=min(tag_count, len(tags))):
                key = (course.id, tag.id)
                if key in existing_links:
                    continue
                link_rows.append(through(course_id=course.id, tag_id=tag.id))

        if link_rows:
            through.objects.bulk_create(link_rows, batch_size=2000, ignore_conflicts=True)

        return courses

    def _seed_course_tree(
        self,
        courses,
        tracks_per_course: int,
        chapters_per_track: int,
        lessons_per_chapter: int,
        tasks_per_lesson: int,
    ):
        from course.models import Chapter, Lesson, Task, Track
        from user.models import Pattern

        pattern = Pattern.objects.filter(code="FC-MASS").first() or Pattern.objects.first()
        if not pattern:
            pattern = Pattern.objects.create(code="FC-MASS", name=f"{DEMO_PREFIX} Massive Pattern")

        # Create tracks
        existing_tracks = set(
            Track.objects.filter(course__in=courses, name__startswith=DEMO_PREFIX).values_list("course_id", "name")
        )
        new_tracks: List[Track] = []
        for cidx, course in enumerate(courses):
            for t in range(tracks_per_course):
                name = f"{DEMO_PREFIX} Track {t + 1} for {course.id}"
                if (course.id, name) in existing_tracks:
                    continue
                new_tracks.append(
                    Track(
                        course=course,
                        pattern=pattern,
                        name=name,
                        description=f"Track {t + 1} for demo course {course.id}.",
                    )
                )
        if new_tracks:
            Track.objects.bulk_create(new_tracks, batch_size=300)

        tracks = list(Track.objects.filter(course__in=courses, name__startswith=DEMO_PREFIX).order_by("id"))

        # Chapters
        existing_chapters = set(
            Chapter.objects.filter(track__in=tracks, name__startswith=DEMO_PREFIX).values_list("track_id", "order")
        )
        new_chapters: List[Chapter] = []
        for track in tracks:
            for order in range(1, chapters_per_track + 1):
                if (track.id, order) in existing_chapters:
                    continue
                new_chapters.append(
                    Chapter(
                        track=track,
                        order=order,
                        name=f"{DEMO_PREFIX} Chapter {order}",
                        description="Demo chapter used to expand navigation coverage.",
                    )
                )
        if new_chapters:
            Chapter.objects.bulk_create(new_chapters, batch_size=500)

        chapters = list(
            Chapter.objects.filter(track__in=tracks, name__startswith=DEMO_PREFIX).order_by("track_id", "order", "id")
        )

        # Lessons
        existing_lessons = set(
            Lesson.objects.filter(chapter__in=chapters, name__startswith=DEMO_PREFIX).values_list("chapter_id", "order")
        )
        new_lessons: List[Lesson] = []
        for chapter in chapters:
            for order in range(1, lessons_per_chapter + 1):
                if (chapter.id, order) in existing_lessons:
                    continue
                playground_type = "Python" if order % 2 else "Jupyter"
                new_lessons.append(
                    Lesson(
                        chapter=chapter,
                        order=order,
                        name=f"{DEMO_PREFIX} Lesson {order}",
                        short_description=f"Demo lesson {order}.",
                        long_description="Long-form demo lesson content. Used to test detail rendering under load.",
                        requirements="None.",
                        video_url=None,
                        blog_link=None,
                        html_content=None,
                        playground_type=playground_type,
                        quote="Ship small, learn fast.",
                        iframe_url=None,
                    )
                )
        if new_lessons:
            Lesson.objects.bulk_create(new_lessons, batch_size=1000)

        lessons = list(
            Lesson.objects.filter(chapter__in=chapters, name__startswith=DEMO_PREFIX).order_by("chapter_id", "order", "id")
        )

        # Tasks
        existing_tasks = set(Task.objects.filter(lesson__in=lessons, name__startswith=DEMO_PREFIX).values_list("lesson_id", "name"))
        new_tasks: List[Task] = []
        for lesson in lessons:
            for t in range(tasks_per_lesson):
                name = f"{DEMO_PREFIX} Task {t + 1}"
                if (lesson.id, name) in existing_tasks:
                    continue
                new_tasks.append(
                    Task(
                        lesson=lesson,
                        name=name,
                        description=f"<p>Demo task {t + 1} for lesson {lesson.id}. Validate rich text rendering.</p>",
                    )
                )
        if new_tasks:
            Task.objects.bulk_create(new_tasks, batch_size=2000)

    def _seed_live_classes(self, count: int):
        from liveclass.models import LiveClass

        existing = LiveClass.objects.filter(name__startswith=DEMO_PREFIX).count()
        if existing >= count:
            return

        to_create: List[LiveClass] = []
        base = date.today()
        for i in range(existing, count):
            start = base + timedelta(days=i % 14)
            to_create.append(
                LiveClass(
                    name=f"{DEMO_PREFIX} Live Class {i + 1:03d}",
                    batch_name=f"{DEMO_PREFIX} Batch {1 + (i % 6)}",
                    start_date=start,
                    duration=14 + (i % 21),
                    daily_start_time=time(18, 0),
                    daily_end_time=time(19, 30),
                    cover_image=None,
                    short_description="Demo live class for schedule testing.",
                    long_description="This is a longer description used to test the live class detail page and enrollment flows.",
                    requirements="Stable internet connection.",
                    medium="English",
                    class_link="https://example.com/live/demo",
                    is_paid=(i % 4) == 0,
                )
            )
        LiveClass.objects.bulk_create(to_create, batch_size=200)

    def _seed_quotes(self, count: int):
        from quote.models import PersonalisedQuote

        existing = PersonalisedQuote.objects.filter(text__startswith=DEMO_PREFIX).count()
        if existing >= count:
            return

        to_create: List[PersonalisedQuote] = []
        for i in range(existing, count):
            to_create.append(
                PersonalisedQuote(
                    text=f"{DEMO_PREFIX} Hello {{name}}, this is quote #{i + 1}. Keep moving."
                )
            )
        PersonalisedQuote.objects.bulk_create(to_create, batch_size=1000)

    def _seed_orders_for_user(self, user):
        from order.models import Order
        from subscription.models import Subscription

        sub = Subscription.objects.order_by("-level").first()
        if not sub:
            return

        existing = Order.objects.filter(order_id__startswith="DEMO-", user=user).count()
        if existing >= 12:
            return

        to_create: List[Order] = []
        for i in range(existing, 12):
            to_create.append(
                Order(
                    order_id=f"DEMO-{user.id}-{timezone.now().strftime('%Y%m%d')}-{i + 1:03d}",
                    user=user,
                    subscription=sub,
                    subscription_type="NEW" if i == 0 else "RENEW",
                    completed=True,
                )
            )
        Order.objects.bulk_create(to_create, batch_size=200)

    def _enroll_user(self, user, courses, enroll_courses: int, enroll_live_classes: int):
        from course.models import UserCourse
        from liveclass.models import LiveClass, UserLiveClass

        selected_courses = courses[: max(0, min(enroll_courses, len(courses)))]
        for idx, course in enumerate(selected_courses):
            progress = round(min(100.0, 5.0 + (idx * 3.7)), 2)
            status = "In Progress" if progress < 100 else "Completed"
            UserCourse.objects.get_or_create(
                user=user,
                course=course,
                defaults={
                    "completed_chapters": 0,
                    "progress": progress,
                    "status": status,
                },
            )

        classes = list(LiveClass.objects.filter(name__startswith=DEMO_PREFIX).order_by("id")[:enroll_live_classes])
        for cidx, live_class in enumerate(classes):
            status = "Approved" if cidx % 3 else "Enrolled"
            UserLiveClass.objects.get_or_create(
                user=user,
                live_class=live_class,
                defaults={"status": status},
            )

