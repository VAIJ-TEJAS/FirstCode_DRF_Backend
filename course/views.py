from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from rest_framework.exceptions import PermissionDenied
from .models import (
    Category, Course, Chapter, Lesson, Task,
    UserCourse, UserChapter, UserLesson, UserTask
)
from .serializers import (
    CategorySerializer, DetailedCourseSerializer, MyDetailedCourseSerializer, MyOverviewCourseSerializer, OverviewCourseSerializer, MyDetailedLessonSerializer, 
    UserCourseSerializer, UserTaskSerializer
)

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    filter_backends = (SearchFilter,)
    search_fields = ['name', 'short_description']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return DetailedCourseSerializer
        return OverviewCourseSerializer

class MyCourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return MyDetailedCourseSerializer
        return MyOverviewCourseSerializer

    def get_queryset(self):
        return Course.objects.filter(usercourse__user=self.request.user)
    

class MyLessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = MyDetailedLessonSerializer

    def retrieve(self, request, *args, **kwargs):
        lesson = self.get_object()
        user = request.user

        # Ensure that only retrieve action is allowed
        if self.request.method != 'GET':
            return Response({'detail': 'Method not allowed.'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

        # Check if the user has started the course for the lesson's chapter
        course = lesson.chapter.track.course
        if not self.user_has_course(user, course):
            raise PermissionDenied("You have not started the course for this lesson.")

        serializer = self.get_serializer(lesson)
        return Response(serializer.data)
    
    def user_has_course(self, user, course):
        return UserCourse.objects.filter(user=user, course=course).exists()


class UserCourseViewSet(viewsets.ModelViewSet):
    queryset = UserCourse.objects.all()
    serializer_class = UserCourseSerializer

    def create(self, request, *args, **kwargs):
        course_id = request.data.get('course')
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({'detail': 'Course not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Use the serializer methods to check enrollment criteria
        serializer = OverviewCourseSerializer(course, context={'request': request})

        can_enroll = serializer.get_can_enroll(course)
        has_already_enrolled = serializer.get_has_already_enrolled(course)
        has_enroll_limit_exceeded = serializer.get_has_enroll_limit_exceeded(request.user.subscriptions.filter(status='Current').first())

        if has_enroll_limit_exceeded:
            return Response({'detail': 'Enrollment limit exceeded.'}, status=status.HTTP_400_BAD_REQUEST)

        if not can_enroll:
            return Response({'detail': 'User cannot enroll in this course.'}, status=status.HTTP_403_FORBIDDEN)

        if has_already_enrolled:
            return Response({'detail': 'User has already enrolled in this course.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create UserCourse instance
        user_course = UserCourse.objects.create(
            user=request.user,
            course=course,
            status='Enrolled'
        )
        
        # Increment enrolled_courses for the user's subscription
        user_subscription = request.user.subscriptions.filter(status='Current').first()
        if user_subscription:
            user_subscription.enrolled_courses += 1
            user_subscription.save()

        serializer = self.get_serializer(user_course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', True)
        instance = self.get_object()
        
        # Check if the action is "Start" and the current status is "Enrolled"
        action = request.data.get('action')
        if action == 'Start':
            if instance.status == 'Enrolled':
                instance.status = 'Started'
                instance.save()
                # Optional: Update any additional fields or handle other logic here
                return Response({'status': 'Course has been started.'}, status=status.HTTP_200_OK)
            else:
                return Response({'detail': 'Course has already been started or is not eligible to start.'}, status=status.HTTP_400_BAD_REQUEST)

        # Default update behavior for other actions
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)


class UserTaskViewSet(viewsets.ModelViewSet):
    queryset = UserTask.objects.all()
    serializer_class = UserTaskSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        task_id = request.data.get('task')

        if not task_id:
            return Response({'detail': 'Task ID is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the Task instance
        task = get_object_or_404(Task, id=task_id)

        # Create or update the UserTask instance
        user_task = UserTask.objects.update_or_create(
            user=request.user,
            task=task,
            defaults={}
        )

        # Retrieve the Lesson instance related to the Task
        lesson = task.lesson

        # Calculate progress for UserLesson
        completed_tasks_count = UserTask.objects.filter(user=request.user, task__lesson=lesson).count()
        total_tasks_count = Task.objects.filter(lesson=lesson).count()
        progress = completed_tasks_count / total_tasks_count if total_tasks_count else 0.0

        # Determine the status based on progress
        lesson_status = 'Completed' if progress == 1 else 'In Progress'

        # Retrieve or create the UserLesson instance
        UserLesson.objects.update_or_create(
            user=request.user,
            lesson=lesson,
            defaults={
                'completed_tasks': completed_tasks_count,
                'progress': progress,
                'status': lesson_status
            }
        )

        # Retrieve the Chapter instance related to the Lesson
        chapter = lesson.chapter

        # Calculate progress for UserChapter
        completed_lessons_count = UserLesson.objects.filter(user=request.user, lesson__chapter=chapter, status='Completed').count()
        total_lessons_count = Lesson.objects.filter(chapter=chapter).count()
        chapter_progress = completed_lessons_count / total_lessons_count if total_lessons_count else 0.0

        # Determine the status based on progress
        chapter_status = 'Completed' if chapter_progress == 1 else 'In Progress'

        # Retrieve or create the UserChapter instance
        UserChapter.objects.update_or_create(
            user=request.user,
            chapter=chapter,
            defaults={
                'completed_lessons': completed_lessons_count,
                'progress': chapter_progress,
                'status': chapter_status
            }
        )

        # Retrieve the Course instance related to the Chapter
        course = chapter.track.course

        # Calculate progress for UserCourse
        completed_chapters_count = UserChapter.objects.filter(user=request.user, chapter__track__course=course, status='Completed').count()
        total_chapters_count = Chapter.objects.filter(track__course=course).count()
        course_progress = completed_chapters_count / total_chapters_count if total_chapters_count else 0.0

        # Determine the status based on progress
        course_status = 'Completed' if course_progress == 1 else 'In Progress'

        # Retrieve or create the UserCourse instance
        UserCourse.objects.update_or_create(
            user=request.user,
            course=course,
            defaults={
                'completed_chapters': completed_chapters_count,
                'progress': course_progress,
                'status': course_status
            }
        )

        # Serialize and return the created or updated UserTask instance
        serializer = self.get_serializer(user_task)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
