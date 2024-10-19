from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django.shortcuts import get_object_or_404
from course.models import UserCourse, UserTask, UserChapter, UserLesson, UserTask

@shared_task
def check_and_reset_inactive_courses():
    # Get the current time and calculate the cutoff time (2 days ago)
    two_days_ago = timezone.now() - timedelta(days=2)

    # Find users who have courses but haven't done any tasks in the last two days
    inactive_user_courses = UserCourse.objects.filter(
        status__in=['Started', 'In Progress'],
        last_modified__lt=two_days_ago
    )

    for user_course in inactive_user_courses:
        # Start over the course if the user has been inactive
        reset_user_course(user_course)


@transaction.atomic
def reset_user_course(user_course):
    """
    Resets the progress of a user's course by deleting their tasks, lessons, and chapters.
    """
    user = user_course.user
    course = user_course.course

    # Delete related UserChapter, UserLesson, and UserTask for this user and course
    user_chapters = UserChapter.objects.filter(chapter__track__course=course, user=user)
    user_lessons = UserLesson.objects.filter(lesson__chapter__track__course=course, user=user)
    user_tasks = UserTask.objects.filter(task__lesson__chapter__track__course=course, user=user)

    # Delete them
    user_chapters.delete()
    user_lessons.delete()
    user_tasks.delete()

    # Optionally reset UserCourse progress, completed chapters, etc.
    user_course.completed_chapters = 0
    user_course.progress = 0.0
    user_course.status = 'Enrolled'  # Reset status to 'Enrolled'
    user_course.save()
