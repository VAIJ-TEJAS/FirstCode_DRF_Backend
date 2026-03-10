import random
import string
from datetime import timedelta, time

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from course.models import (
    Category,
    Chapter,
    Course,
    Lesson,
    Tag,
    Task,
    Track,
    UserChapter,
    UserCourse,
    UserLesson,
    UserTask,
)
from liveclass.models import LiveClass, UserLiveClass
from order.models import Order
from otp.models import OTP, PasswordResetToken
from quote.models import PersonalisedQuote
from subscription.models import Subscription, UserSubscription
from user.models import Pattern, UserProfile


class Command(BaseCommand):
    help = "Load heavy dummy data into the database for local development/testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=50,
            help="Number of dummy users to create (default: 50).",
        )
        parser.add_argument(
            "--courses",
            type=int,
            default=20,
            help="Number of dummy courses to create (default: 20).",
        )

    def handle(self, *args, **options):
        user_count = options["users"]
        course_count = options["courses"]

        self.stdout.write(self.style.WARNING("Starting heavy dummy data generation..."))

        patterns = self._create_patterns()
        subscriptions = self._create_subscriptions()
        categories, tags = self._create_categories_and_tags()
        courses = self._create_courses(course_count, categories, tags, patterns)
        users = self._create_users(user_count, patterns)
        self._create_quotes()
        self._enroll_users_in_courses(users, courses)
        self._create_subscriptions_for_users(users, subscriptions)
        self._create_live_classes(users)
        self._create_orders(users, subscriptions)
        self._create_otps_and_tokens(users)

        self.stdout.write(self.style.SUCCESS("Dummy data generation complete."))

    def _create_patterns(self):
        pattern_names = [
            "Beginner",
            "Intermediate",
            "Advanced",
            "Career Switcher",
            "Hobby Learner",
        ]
        patterns = []
        for idx, name in enumerate(pattern_names, start=1):
            code = f"PATTERN_{idx}"
            pattern, _ = Pattern.objects.get_or_create(
                code=code,
                defaults={
                    "name": name,
                    "description": f"{name} learning pattern for FirstCode.",
                },
            )
            patterns.append(pattern)
        return patterns

    def _create_subscriptions(self):
        subscription_specs = [
            ("Starter", 30, 999, 3, 5, 0),
            ("Pro", 90, 2499, 10, 20, 1),
            ("Elite", 180, 4999, 25, 50, 2),
        ]
        subscriptions = []
        for name, validity, price, start_limit, enroll_limit, level in subscription_specs:
            subscription, _ = Subscription.objects.get_or_create(
                name=name,
                defaults={
                    "description": f"{name} subscription plan.",
                    "validity": validity,
                    "price": price,
                    "start_limit": start_limit,
                    "enroll_limit": enroll_limit,
                    "level": level,
                },
            )
            subscriptions.append(subscription)
        return subscriptions

    def _create_categories_and_tags(self):
        category_names = [
            "Programming",
            "Data Science",
            "Web Development",
            "DevOps",
            "Career",
        ]
        tag_names = [
            "Python",
            "Django",
            "React",
            "APIs",
            "Docker",
            "Kubernetes",
            "Pandas",
            "SQL",
        ]

        categories = []
        for name in category_names:
            category, _ = Category.objects.get_or_create(
                name=name,
                defaults={"description": f"{name} related courses."},
            )
            categories.append(category)

        tags = []
        for name in tag_names:
            tag, _ = Tag.objects.get_or_create(
                name=name,
                defaults={"description": f"Courses related to {name}."},
            )
            tags.append(tag)

        return categories, tags

    def _create_courses(self, course_count, categories, tags, patterns):
        courses = []
        main_categories = ["Professional", "Personal"]
        for idx in range(course_count):
            category = random.choice(categories)
            main_category = random.choice(main_categories)
            name = f"{category.name} Course {idx + 1}"
            course, _ = Course.objects.get_or_create(
                name=name,
                defaults={
                    "category": category,
                    "main_category": main_category,
                    "short_description": f"Short description for {name}.",
                    "long_description": f"Long description for {name}.",
                    "requirements": "A laptop and willingness to learn.",
                    "is_paid": random.choice([True, False]),
                },
            )
            if not course.tags.exists():
                sample_tags = random.sample(
                    tags, k=min(len(tags), random.randint(2, 4))
                )
                course.tags.add(*sample_tags)

            self._create_tracks_chapters_lessons_tasks(course, patterns)
            courses.append(course)
        return courses

    def _create_tracks_chapters_lessons_tasks(self, course, patterns):
        track_count = random.randint(1, 3)
        for t_idx in range(track_count):
            pattern = random.choice(patterns)
            track_name = f"{course.name} - Track {t_idx + 1}"
            track, _ = Track.objects.get_or_create(
                course=course,
                pattern=pattern,
                name=track_name,
                defaults={"description": f"{track_name} description."},
            )

            chapter_count = random.randint(3, 6)
            for c_idx in range(chapter_count):
                chapter_name = f"{track.name} - Chapter {c_idx + 1}"
                chapter, _ = Chapter.objects.get_or_create(
                    track=track,
                    order=c_idx,
                    defaults={
                        "name": chapter_name,
                        "description": f"{chapter_name} description.",
                    },
                )

                lesson_count = random.randint(3, 5)
                for l_idx in range(lesson_count):
                    lesson_name = f"{chapter.name} - Lesson {l_idx + 1}"
                    playground_type = random.choice(["Python", "Jupyter"])
                    lesson, _ = Lesson.objects.get_or_create(
                        chapter=chapter,
                        order=l_idx,
                        defaults={
                            "name": lesson_name,
                            "short_description": f"{lesson_name} short description.",
                            "long_description": f"{lesson_name} long description.",
                            "requirements": "Basic understanding of previous lessons.",
                            "playground_type": playground_type,
                        },
                    )

                    task_count = random.randint(2, 4)
                    for task_idx in range(task_count):
                        task_name = f"{lesson.name} - Task {task_idx + 1}"
                        Task.objects.get_or_create(
                            lesson=lesson,
                            name=task_name,
                            defaults={
                                "description": f"<p>{task_name} rich description.</p>"
                            },
                        )

    def _create_users(self, user_count, patterns):
        users = []
        for idx in range(user_count):
            username = f"testuser{idx + 1}"
            email = f"{username}@example.com"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": email},
            )
            if created:
                user.set_password("password123")
                user.save()

            pattern = random.choice(patterns)
            UserProfile.objects.get_or_create(
                user=user,
                defaults={"pattern": pattern},
            )

            users.append(user)
        return users

    def _create_quotes(self):
        quote_texts = [
            "Hello, {name}, keep pushing your limits today!",
            "{name}, every bug you fix makes you stronger.",
            "Stay curious, {name}, and keep building.",
            "{name}, remember: practice makes progress, not perfection.",
        ]
        for text in quote_texts:
            PersonalisedQuote.objects.get_or_create(text=text)

    def _enroll_users_in_courses(self, users, courses):
        for user in users:
            user_courses = random.sample(
                courses, k=min(len(courses), random.randint(3, 7))
            )
            for course in user_courses:
                status = random.choice(
                    ["Enrolled", "Started", "In Progress", "Completed"]
                )
                progress = random.uniform(0, 100)
                user_course, _ = UserCourse.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={
                        "status": status,
                        "progress": round(progress, 2),
                    },
                )

                chapters = Chapter.objects.filter(track__course=course)
                for chapter in chapters:
                    chapter_progress = random.uniform(0, 100)
                    UserChapter.objects.get_or_create(
                        user=user,
                        chapter=chapter,
                        defaults={
                            "completed_lessons": random.randint(0, 10),
                            "progress": round(chapter_progress, 2),
                        },
                    )

                lessons = Lesson.objects.filter(chapter__track__course=course)
                for lesson in lessons:
                    lesson_progress = random.uniform(0, 100)
                    user_lesson, _ = UserLesson.objects.get_or_create(
                        user=user,
                        lesson=lesson,
                        defaults={
                            "completed_tasks": random.randint(0, 10),
                            "progress": round(lesson_progress, 2),
                        },
                    )

                    tasks = Task.objects.filter(lesson=lesson)
                    for task in tasks:
                        UserTask.objects.get_or_create(
                            user=user,
                            task=task,
                        )

    def _create_subscriptions_for_users(self, users, subscriptions):
        now = timezone.now()
        for user in users:
            current_sub = random.choice(subscriptions)
            expired_sub = random.choice(subscriptions)
            upcoming_sub = random.choice(subscriptions)

            current_start = now - timedelta(days=5)
            current_end = now + timedelta(days=current_sub.validity)
            upcoming_start = now + timedelta(days=7)
            upcoming_end = upcoming_start + timedelta(days=upcoming_sub.validity)
            expired_start = now - timedelta(days=expired_sub.validity + 30)
            expired_end = expired_start + timedelta(days=expired_sub.validity)

            current_us, _ = UserSubscription.objects.get_or_create(
                user=user,
                subscription=current_sub,
                status="Current",
                defaults={
                    "subscription_start_date": current_start,
                    "subscription_end_date": current_end,
                    "renewed": False,
                    "payment": {"amount": current_sub.price, "currency": "INR"},
                },
            )

            UserSubscription.objects.get_or_create(
                user=user,
                subscription=expired_sub,
                status="Expired",
                defaults={
                    "subscription_start_date": expired_start,
                    "subscription_end_date": expired_end,
                    "renewed": random.choice([True, False]),
                    "payment": {"amount": expired_sub.price, "currency": "INR"},
                },
            )

            UserSubscription.objects.get_or_create(
                user=user,
                subscription=upcoming_sub,
                status="Upcoming",
                defaults={
                    "subscription_start_date": upcoming_start,
                    "subscription_end_date": upcoming_end,
                    "renewed": False,
                    "payment": {"amount": upcoming_sub.price, "currency": "INR"},
                },
            )

            profile = UserProfile.objects.filter(user=user).first()
            if profile and not profile.current_subscription:
                profile.current_subscription = current_us
                profile.save(update_fields=["current_subscription"])

    def _create_live_classes(self, users):
        today = timezone.now().date()
        live_class_specs = [
            ("Python Bootcamp", "Batch A"),
            ("Django Deep Dive", "Batch B"),
            ("Data Science 101", "Batch C"),
            ("System Design", "Batch D"),
        ]

        live_classes = []
        for name, batch in live_class_specs:
            live_class, _ = LiveClass.objects.get_or_create(
                name=name,
                batch_name=batch,
                defaults={
                    "start_date": today + timedelta(days=random.randint(1, 10)),
                    "duration": random.randint(5, 30),
                    "daily_start_time": time(hour=19, minute=0),
                    "daily_end_time": time(hour=21, minute=0),
                    "short_description": f"{name} for {batch}.",
                    "long_description": f"Intensive live class: {name} ({batch}).",
                    "requirements": "Stable internet connection and Zoom.",
                    "medium": "English",
                    "class_link": "https://example.com/live-class",
                    "is_paid": random.choice([True, False]),
                },
            )
            live_classes.append(live_class)

        for live_class in live_classes:
            enrolled_users = random.sample(
                users, k=min(len(users), random.randint(10, 25))
            )
            for user in enrolled_users:
                status = random.choice(
                    ["Enrolled", "Approved", "Attended", "Completed"]
                )
                UserLiveClass.objects.get_or_create(
                    user=user,
                    live_class=live_class,
                    defaults={"status": status},
                )

    def _create_orders(self, users, subscriptions):
        for user in users:
            order_count = random.randint(1, 3)
            for _ in range(order_count):
                subscription = random.choice(subscriptions)
                order_id = self._generate_order_id(user)
                Order.objects.get_or_create(
                    order_id=order_id,
                    user=user,
                    subscription=subscription,
                    defaults={
                        "subscription_type": random.choice(["NEW", "RENEW"]),
                        "completed": random.choice([True, False]),
                    },
                )

    def _create_otps_and_tokens(self, users):
        now = timezone.now()
        for user in users:
            email = user.email
            if not email:
                continue

            OTP.objects.create(
                code=self._random_code(6),
                email=email,
                created_at=now,
                expires_at=now + timedelta(minutes=10),
                is_used=random.choice([True, False]),
            )

            PasswordResetToken.objects.create(
                email=email,
                token=self._random_token(),
                expires_at=now + timedelta(hours=1),
                is_used=random.choice([True, False]),
            )

    def _generate_order_id(self, user):
        random_part = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ORD-{user.id}-{random_part}"

    def _random_code(self, length):
        return "".join(random.choices(string.digits, k=length))

    def _random_token(self, length=32):
        return "".join(
            random.choices(string.ascii_letters + string.digits, k=length)
        )

