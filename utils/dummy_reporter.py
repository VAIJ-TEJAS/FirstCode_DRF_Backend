from django.core.management.base import BaseCommand
from django.utils import timezone

from course.models import Course, Lesson, UserCourse, UserLesson
from liveclass.models import LiveClass, UserLiveClass
from subscription.models import Subscription, UserSubscription
from user.models import UserProfile


class Command(BaseCommand):
    help = (
        "Prints a simple text report about how many dummy records exist "
        "for main learning objects. This is only for local testing."
    )

    def handle(self, *args, **options):
        now = timezone.now()
        self.stdout.write(f"Dummy data report at {now.isoformat()}")
        self.stdout.write("-" * 60)

        course_count = Course.objects.count()
        lesson_count = Lesson.objects.count()
        user_course_count = UserCourse.objects.count()
        user_lesson_count = UserLesson.objects.count()
        profile_count = UserProfile.objects.count()

        live_class_count = LiveClass.objects.count()
        user_live_class_count = UserLiveClass.objects.count()

        subscription_count = Subscription.objects.count()
        user_subscription_count = UserSubscription.objects.count()

        self.stdout.write(f"Courses: {course_count}")
        self.stdout.write(f"Lessons: {lesson_count}")
        self.stdout.write(f"UserCourse: {user_course_count}")
        self.stdout.write(f"UserLesson: {user_lesson_count}")
        self.stdout.write(f"UserProfile: {profile_count}")
        self.stdout.write("")
        self.stdout.write(f"LiveClass: {live_class_count}")
        self.stdout.write(f"UserLiveClass: {user_live_class_count}")
        self.stdout.write("")
        self.stdout.write(f"Subscription plans: {subscription_count}")
        self.stdout.write(f"UserSubscription: {user_subscription_count}")
