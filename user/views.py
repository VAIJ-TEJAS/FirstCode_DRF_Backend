from datetime import timedelta
from calendar import monthrange
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta, datetime
from course.models import Course, UserChapter, UserCourse, UserLesson, UserTask
from course.serializers import (
    OverviewCourseSerializer,
    UserChapterSerializer,
    UserCourseSerializer,
    UserLessonSerializer,
    UserTaskSerializer,
)
from liveclass.models import LiveClass, UserLiveClass
from liveclass.serializers import LiveClassSerializer, UserLiveClassSerializer
from subscription.models import UserSubscription
from .models import Pattern, UserProfile
from itertools import chain
from operator import attrgetter
from django.contrib.auth import login
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from .serializers import UserProfileSerializer, UserSerializer
from rest_framework.decorators import api_view, permission_classes
from google.oauth2 import id_token
from google.auth.transport import requests
import os


class Signup(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["post"]

    def create(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.create_user(**serializer.validated_data)
        token = Token.objects.create(user=user)

        # Create UserProfile for the user
        UserProfile.objects.create(user=user)

        # Fetch the subscription with level 0
        try:
            default_subscription = UserSubscription.objects.get(level=0)
        except UserSubscription.DoesNotExist:
            return Response(
                {"error": "Default subscription not found"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # Assign the subscription to the user
        UserSubscription.objects.create(
            user=user,
            subscription=default_subscription.subscription,
            amount=default_subscription.subscription.price,
            subscription_start_date=timezone.now(),
            subscription_end_date=timezone.now()
            + timedelta(days=default_subscription.subscription.validity),
            status="Current",
        )

        # Serialize the user object
        user_serializer = UserSerializer(token.user)
        serialized_user = user_serializer.data

        return Response({"token": token.key, "user": serialized_user})


class Signin(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super(Signin, self).post(request, *args, **kwargs)
        old_token = response.data["token"]

        # Get the user associated with this token
        old_token = Token.objects.get(key=old_token)
        user = old_token.user

        # Update the last_login field
        user.last_login = timezone.now()
        user.save()

        # Delete the old token and create a new one
        # old_token.delete()
        # new_token = Token.objects.create(user=user)

        # Serialize the user object
        user_serializer = UserSerializer(user)
        serialized_user = user_serializer.data

        return Response({"token": old_token.key, "user": serialized_user})


@api_view(["POST"])
@permission_classes([AllowAny])
def google_complete(request):
    client_id = os.getenv("GOOGLE_OAUTH2_KEY")

    token = request.data.get("token")

    if not token:
        print("Token is missing")
        return Response({"error": "Token is missing"}, status=400)

    # Validate the token and get user info
    try:
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), client_id)

        # idinfo['sub'] is user's Google ID
        email = idinfo["email"]
        first_name = idinfo.get("given_name", "")
        last_name = idinfo.get("family_name", "")

        # Try to retrieve the user by their email
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "first_name": first_name, "last_name": last_name},
        )

        if created:
            user.set_unusable_password()  # Important if password login isn't meant to be used
            user.save()

        # Authenticate session
        login(request, user)

        # Create a token for your DRF TokenAuthentication
        token, created = Token.objects.get_or_create(user=user)

        # Serialize the user object
        user_serializer = UserSerializer(token.user)
        serialized_user = user_serializer.data

        return Response({"token": token.key, "user": serialized_user})

    except ValueError:
        # Invalid token
        print("Invalid token")
        return Response({"error": "Invalid token"}, status=400)


class UserNameUpdateViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ["post"]

    def create(self, request, *args, **kwargs):
        user = self.request.user
        profile = UserProfile.objects.get(user=user)

        # Check if the user has changed their name in the last 30 days
        if profile.last_name_change:
            one_month_ago = timezone.now() - timedelta(days=30)
            if profile.last_name_change > one_month_ago:
                return Response(
                    {"detail": "You can only change your name once every 30 days."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Proceed to update the user's name
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update the last_name_change field in UserProfile
        profile.last_name_change = timezone.now()
        profile.save()

        return Response(serializer.data)


class UserDeleteViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    http_method_names = ["post"]

    def create(self, request, *args, **kwargs):
        user = self.request.user

        # Ensure UserProfile is saved
        profile, created = UserProfile.objects.get_or_create(user=user)

        # Delete the associated UserProfile
        profile.delete()

        # Delete the user
        user.delete()

        # Optionally, delete all tokens related to the user
        Token.objects.filter(user_id=user.id).delete()

        return Response(
            {"detail": "Account successfully deleted."},
            status=status.HTTP_204_NO_CONTENT,
        )


class PatternAssignmentViewSet(
    viewsets.GenericViewSet, viewsets.mixins.CreateModelMixin
):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    http_method_names = ["post"]

    def create(self, request, *args, **kwargs):
        user = self.request.user
        pattern_code = request.data.get(
            "pattern_code"
        )  # Get the pattern_code from request

        if not pattern_code:
            return Response(
                {"detail": "Pattern code is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Look up the pattern by code
        pattern = get_object_or_404(Pattern, code=pattern_code)

        # Get or create the user profile
        profile, created = UserProfile.objects.get_or_create(user=user)

        # Assign the pattern to the user profile
        profile.pattern = pattern
        profile.save()

        return Response(
            {"detail": "Pattern assigned successfully."}, status=status.HTTP_200_OK
        )


class LearningProgressGraphViewSet(
    viewsets.GenericViewSet, viewsets.mixins.ListModelMixin
):
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        two_weeks_ago = today - timedelta(days=14)

        # Get lessons completed by the user in the past two weeks
        lessons_completed = (
            UserLesson.objects.filter(
                user=user,
                last_modified__date__range=[two_weeks_ago, today],
                status="Completed",
            )
            .values("last_modified__date")
            .annotate(completed_count=Count("id"))
            .order_by("last_modified__date")
        )

        # Create a dictionary to hold the data for the past 14 days
        progress_data = {}
        for i in range(15):
            day = two_weeks_ago + timedelta(days=i)
            progress_data[day] = {"date": day, "completed_lessons": 0, "comparison": 0}

        # Populate the data with the actual completed lessons
        for lesson in lessons_completed:
            date = lesson["last_modified__date"]
            completed_count = lesson["completed_count"]
            progress_data[date]["completed_lessons"] = completed_count

        # Calculate the comparison with the previous day
        previous_day_lessons = 0
        for day, data in progress_data.items():
            data["comparison"] = data["completed_lessons"] - previous_day_lessons
            previous_day_lessons = data["completed_lessons"]

        # Convert the data to a list and exclude future dates
        progress_list = [data for day, data in progress_data.items() if day <= today]

        return Response(progress_list, status=status.HTTP_200_OK)


class MonthlyProgressViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        user = request.user

        # Optionally, get the year and month from query parameters (default to the current month)
        year = int(request.query_params.get("year", timezone.now().year))
        month = int(request.query_params.get("month", timezone.now().month))

        # Determine the first and last days of the month
        first_day = datetime(year, month, 1).date()
        last_day = datetime(year, month, monthrange(year, month)[1]).date()

        # Get lessons completed by the user in the specified month
        lessons_completed = (
            UserLesson.objects.filter(
                user=user,
                last_modified__date__range=[first_day, last_day],
                status="Completed",
            )
            .values("last_modified__date")
            .annotate(completed_count=Count("id"))
            .order_by("last_modified__date")
        )

        # Create a dictionary to hold the data for each day of the month
        progress_data = {}
        for day in range(1, last_day.day + 1):
            date = datetime(year, month, day).date()
            progress_data[date] = {"date": date, "completed_lessons": 0}

        # Populate the data with the actual completed lessons
        for lesson in lessons_completed:
            date = lesson["last_modified__date"]
            completed_count = lesson["completed_count"]
            progress_data[date]["completed_lessons"] = completed_count

        # Convert the data to a list
        progress_list = list(progress_data.values())

        return Response(progress_list, status=status.HTTP_200_OK)


class PieChartViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        user = request.user

        # Query for courses by status
        enrolled_courses = UserCourse.objects.filter(
            user=user, status="Enrolled"
        ).count()
        started_courses = UserCourse.objects.filter(user=user, status="Started").count()
        in_progress_courses = UserCourse.objects.filter(
            user=user, status="In Progress"
        ).count()
        completed_courses = UserCourse.objects.filter(
            user=user, status="Completed"
        ).count()

        # Query for total enrolled classes (lessons)
        enrolled_classes = UserLesson.objects.filter(user=user).count()

        # Retrieve the active subscription for the user
        active_subscription = UserSubscription.objects.filter(
            user=user, status="Current"
        ).first()

        # Initialize limits
        course_limit = 0
        class_limit = 0

        if active_subscription:
            course_limit = active_subscription.subscription.start_limit
            class_limit = active_subscription.subscription.enroll_limit

        # Structure the response data
        overview_data = {
            "started_courses": started_courses,
            "enrolled_courses": enrolled_courses,
            "in_progress_courses": in_progress_courses,
            "completed_courses": completed_courses,
            "enrolled_classes": enrolled_classes,
            "course_limit": course_limit,
            "class_limit": class_limit,
        }

        return Response(overview_data, status=status.HTTP_200_OK)


class EventViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        user = request.user
        overview = request.query_params.get("overview", None)

        # Get the user's completed courses, chapters, lessons, tasks, and live classes
        courses = UserCourse.objects.filter(user=user, status="Completed").order_by(
            "-last_modified"
        )
        chapters = UserChapter.objects.filter(user=user, status="Completed").order_by(
            "-last_modified"
        )
        lessons = UserLesson.objects.filter(user=user, status="Completed").order_by(
            "-last_modified"
        )
        tasks = UserTask.objects.filter(user=user).order_by("-last_modified")
        live_classes = UserLiveClass.objects.filter(
            user=user, status="Completed"
        ).order_by("-last_modified")

        # Combine all the querysets into a single list, sorted by last_modified
        events = sorted(
            chain(courses, chapters, lessons, tasks, live_classes),
            key=attrgetter("last_modified"),
            reverse=True,
        )

        # If overview is present in query params, limit the results to the latest 5
        if overview:
            events = events[:5]

        # Serialize each event type with its respective serializer and add a `type` field
        serialized_events = []
        for event in events:
            if isinstance(event, UserCourse):
                serialized_data = UserCourseSerializer(event).data
                serialized_data["type"] = "course"
                serialized_data["description"] = f"{event.course.name}"
            elif isinstance(event, UserChapter):
                serialized_data = UserChapterSerializer(event).data
                serialized_data["type"] = "chapter"
                serialized_data["description"] = f"{event.chapter.name}"
            elif isinstance(event, UserLesson):
                serialized_data = UserLessonSerializer(event).data
                serialized_data["type"] = "lesson"
                serialized_data["description"] = f"{event.lesson.name} in chapter {event.lesson.chapter.name}"
            elif isinstance(event, UserTask):
                serialized_data = UserTaskSerializer(event).data
                serialized_data["type"] = "task"
                serialized_data["description"] = f"{event.task.name}"
            elif isinstance(event, UserLiveClass):
                serialized_data = UserLiveClassSerializer(event).data
                serialized_data["type"] = "live_class"
                serialized_data["description"] = f"Attended live class - {event.live_class.name}"

            serialized_events.append(serialized_data)

        return Response(serialized_events, status=status.HTTP_200_OK)


class LeftCoursesViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        user = request.user

        # Fetch UserCourse objects that are not completed (i.e., where the user left off)
        left_courses = (
            UserCourse.objects.filter(user=user)
            .exclude(status="Completed")
            .order_by("-last_modified")
        )

        # Serialize the data
        serialized_courses = UserCourseSerializer(left_courses, many=True).data

        return Response(serialized_courses, status=status.HTTP_200_OK)


class LatestCoursesAndClassesViewSet(
    viewsets.GenericViewSet, viewsets.mixins.ListModelMixin
):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        # Retrieve the latest courses and classes
        latest_courses = Course.objects.all().order_by("-created_at")[:4]
        latest_classes = LiveClass.objects.all().order_by("-created_at")[:4]

        # Combine the latest courses and classes
        combined_items = list(latest_courses) + list(latest_classes)

        # Sort combined items by creation date (latest first)
        combined_items = sorted(
            combined_items, key=attrgetter("created_at"), reverse=True
        )[:4]

        # Serialize each item with the appropriate serializer
        serialized_items = []
        for item in combined_items:
            if isinstance(item, Course):
                serialized_items.append(OverviewCourseSerializer(item).data)
            elif isinstance(item, LiveClass):  # Adjust if 'Class' has a different name
                serialized_items.append(LiveClassSerializer(item).data)

        return Response(serialized_items, status=status.HTTP_200_OK)


class StreakViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get"]

    def list(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        
        # Initialize streak counters and date ranges
        streak = 0
        longest_streak = 0
        current_streak = 0

        current_streak_start = None
        current_streak_end = None
        longest_streak_start = None
        longest_streak_end = None

        # Get all lessons completed by the user, ordered by date
        completed_lessons_by_day = UserLesson.objects.filter(
            user=user, status="Completed"
        ).order_by("-last_modified__date")

        if not completed_lessons_by_day.exists():
            # No completed lessons, return streak of 0 and no date range
            return Response({
                "current_streak": 0,
                "current_streak_dates": None,
                "longest_streak": 0,
                "longest_streak_dates": None
            }, status=status.HTTP_200_OK)

        # Track consecutive streak dates
        previous_day = None
        longest_streak_temp = 0
        current_streak_tracking = True

        # Loop through each completed lesson date and check for consecutive days
        for lesson in completed_lessons_by_day:
            completed_day = lesson.last_modified.date()

            # If it's the first iteration or consecutive day, increase streak counters
            if previous_day is None or (previous_day - timedelta(days=1)) == completed_day:
                longest_streak_temp += 1

                # Check for the longest streak update
                if longest_streak_temp > longest_streak:
                    longest_streak = longest_streak_temp
                    longest_streak_start = completed_day
                    longest_streak_end = previous_day if previous_day else completed_day

                # Track the current streak if within the latest consecutive days
                if current_streak_tracking:
                    if current_streak == 0:
                        current_streak_end = completed_day
                    current_streak_start = completed_day
                    current_streak += 1
                    streak += 1
            else:
                # Reset the temp counter for the longest streak
                longest_streak_temp = 1

                # Stop tracking current streak if break in consecutive days
                if current_streak_tracking:
                    current_streak_tracking = False

            # Update previous day
            previous_day = completed_day

        # Format dates as "Oct 2 - Oct 11"
        def format_date_range(start_date, end_date):
            if start_date and end_date:
                return f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d')}"
            return None

        streak_data = {
            "current_streak": streak,
            "current_streak_dates": format_date_range(current_streak_start, current_streak_end),
            "longest_streak": longest_streak + 1,
            "longest_streak_dates": format_date_range(longest_streak_start, longest_streak_end),
        }

        return Response(streak_data, status=status.HTTP_200_OK)

