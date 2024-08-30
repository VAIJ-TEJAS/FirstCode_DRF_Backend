from datetime import timedelta
from calendar import monthrange
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta, datetime
from course.models import Course, UserChapter, UserCourse, UserLesson, UserTask
from course.serializers import OverviewCourseSerializer, UserChapterSerializer, UserCourseSerializer, UserLessonSerializer, UserTaskSerializer
from liveclass.models import LiveClass, UserLiveClass
from liveclass.serializers import LiveClassSerializer, UserLiveClassSerializer
from subscription.models import UserSubscription
from .models import Pattern, UserProfile
from itertools import chain
from operator import attrgetter
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from .serializers import UserProfileSerializer, UserSerializer

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
        
        return Response({"detail": "Account successfully deleted."}, status=status.HTTP_204_NO_CONTENT)


class PatternAssignmentViewSet(viewsets.GenericViewSet, viewsets.mixins.CreateModelMixin):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        user = self.request.user
        pattern_name = request.data.get('pattern_name')

        if not pattern_name:
            return Response({"detail": "Pattern name is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Look up the pattern by name
        pattern = get_object_or_404(Pattern, name=pattern_name)

        # Get or create the user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Assign the pattern to the user profile
        profile.pattern = pattern
        profile.save()

        return Response({"detail": "Pattern assigned successfully."}, status=status.HTTP_200_OK)

class LearningProgressGraphViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        user = request.user
        today = timezone.now().date()
        two_weeks_ago = today - timedelta(days=14)

        # Get lessons completed by the user in the past two weeks
        lessons_completed = (
            UserLesson.objects.filter(user=user, last_modified__date__range=[two_weeks_ago, today], status='Completed')
            .values('last_modified__date')
            .annotate(completed_count=Count('id'))
            .order_by('last_modified__date')
        )

        # Create a dictionary to hold the data for the past 14 days
        progress_data = {}
        for i in range(15):
            day = two_weeks_ago + timedelta(days=i)
            progress_data[day] = {"date": day, "completed_lessons": 0, "comparison": 0}

        # Populate the data with the actual completed lessons
        for lesson in lessons_completed:
            date = lesson['last_modified__date']
            completed_count = lesson['completed_count']
            progress_data[date]["completed_lessons"] = completed_count

        # Calculate the comparison with the previous day
        previous_day_lessons = 0
        for day, data in progress_data.items():
            data["comparison"] = data["completed_lessons"] - previous_day_lessons
            previous_day_lessons = data["completed_lessons"]

        # Convert the data to a list and exclude future dates
        progress_list = [
            data for day, data in progress_data.items() if day <= today
        ]

        return Response(progress_list, status=status.HTTP_200_OK)
    
class MonthlyProgressViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        user = request.user
        
        # Optionally, get the year and month from query parameters (default to the current month)
        year = int(request.query_params.get('year', timezone.now().year))
        month = int(request.query_params.get('month', timezone.now().month))
        
        # Determine the first and last days of the month
        first_day = datetime(year, month, 1).date()
        last_day = datetime(year, month, monthrange(year, month)[1]).date()

        # Get lessons completed by the user in the specified month
        lessons_completed = (
            UserLesson.objects.filter(user=user, last_modified__date__range=[first_day, last_day], status='Completed')
            .values('last_modified__date')
            .annotate(completed_count=Count('id'))
            .order_by('last_modified__date')
        )

        # Create a dictionary to hold the data for each day of the month
        progress_data = {}
        for day in range(1, last_day.day + 1):
            date = datetime(year, month, day).date()
            progress_data[date] = {"date": date, "completed_lessons": 0}

        # Populate the data with the actual completed lessons
        for lesson in lessons_completed:
            date = lesson['last_modified__date']
            completed_count = lesson['completed_count']
            progress_data[date]["completed_lessons"] = completed_count

        # Convert the data to a list
        progress_list = list(progress_data.values())

        return Response(progress_list, status=status.HTTP_200_OK)
    
class PieChartViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        user = request.user

        # Query for courses by status
        enrolled_courses = UserCourse.objects.filter(user=user, status='Enrolled').count()
        started_courses = UserCourse.objects.filter(user=user, status='Started').count()
        in_progress_courses = UserCourse.objects.filter(user=user, status='In Progress').count()
        completed_courses = UserCourse.objects.filter(user=user, status='Completed').count()

        # Query for total enrolled classes (lessons)
        enrolled_classes = UserLesson.objects.filter(user=user).count()

        # Retrieve the active subscription for the user
        active_subscription = UserSubscription.objects.filter(user=user, status='Current').first()

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
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        user = request.user
        overview = request.query_params.get('overview', None)

        # Get the user's completed courses, chapters, lessons, tasks, and live classes
        courses = UserCourse.objects.filter(user=user, status='Completed').order_by('-last_modified')
        chapters = UserChapter.objects.filter(user=user, status='Completed').order_by('-last_modified')
        lessons = UserLesson.objects.filter(user=user, status='Completed').order_by('-last_modified')
        tasks = UserTask.objects.filter(user=user).order_by('-last_modified')
        live_classes = UserLiveClass.objects.filter(user=user, status='Completed').order_by('-last_modified')

        # Combine all the querysets into a single list, sorted by last_modified
        events = sorted(
            chain(courses, chapters, lessons, tasks, live_classes),
            key=attrgetter('last_modified'),
            reverse=True
        )

        # If overview is present in query params, limit the results to the latest 5
        if overview:
            events = events[:5]

        # Serialize each event type with its respective serializer and add a `type` field
        serialized_events = []
        for event in events:
            if isinstance(event, UserCourse):
                serialized_data = UserCourseSerializer(event).data
                serialized_data['type'] = 'course'
            elif isinstance(event, UserChapter):
                serialized_data = UserChapterSerializer(event).data
                serialized_data['type'] = 'chapter'
            elif isinstance(event, UserLesson):
                serialized_data = UserLessonSerializer(event).data
                serialized_data['type'] = 'lesson'
            elif isinstance(event, UserTask):
                serialized_data = UserTaskSerializer(event).data
                serialized_data['type'] = 'task'
            elif isinstance(event, UserLiveClass):
                serialized_data = UserLiveClassSerializer(event).data
                serialized_data['type'] = 'live_class'

            serialized_events.append(serialized_data)

        return Response(serialized_events, status=status.HTTP_200_OK)
    
class LeftCoursesViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        user = request.user

        # Fetch UserCourse objects that are not completed (i.e., where the user left off)
        left_courses = UserCourse.objects.filter(user=user).exclude(status='Completed').order_by('-last_modified')

        # Serialize the data
        serialized_courses = UserCourseSerializer(left_courses, many=True).data

        return Response(serialized_courses, status=status.HTTP_200_OK)
    

class LatestCoursesAndClassesViewSet(viewsets.GenericViewSet, viewsets.mixins.ListModelMixin):
    permission_classes = [IsAuthenticated]
    http_method_names = ['get']

    def list(self, request, *args, **kwargs):
        # Retrieve the latest courses and classes
        latest_courses = Course.objects.all().order_by('-created_at')[:4]
        latest_classes = LiveClass.objects.all().order_by('-created_at')[:4]
        
        # Combine the latest courses and classes
        combined_items = list(latest_courses) + list(latest_classes)
        
        # Sort combined items by creation date (latest first)
        combined_items = sorted(combined_items, key=attrgetter('created_at'), reverse=True)[:4]

        # Serialize each item with the appropriate serializer
        serialized_items = []
        for item in combined_items:
            if isinstance(item, Course):
                serialized_items.append(OverviewCourseSerializer(item).data)
            elif isinstance(item, LiveClass):  # Adjust if 'Class' has a different name
                serialized_items.append(LiveClassSerializer(item).data)

        return Response(serialized_items, status=status.HTTP_200_OK)