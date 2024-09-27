from rest_framework import serializers

from user.serializers import PatternSerializer
from .models import (
    Category,
    Tag,
    Course,
    Track,
    Chapter,
    Lesson,
    File,
    Task,
    UserCourse,
    UserChapter,
    UserLesson,
    UserTask,
)


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = "__all__"


class FileSerializer(serializers.ModelSerializer):
    class Meta:
        model = File
        fields = "__all__"


class MyTaskSerializer(serializers.ModelSerializer):
    user_task = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = "__all__"

    def get_user_task(self, obj):
        user_task = UserTask.objects.filter(
            task=obj, user=self.context["request"].user
        ).first()
        serializer = UserTaskSerializer(user_task)
        return serializer.data


class OverviewLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ["id", "name"]


class MyOverviewLessonSerializer(serializers.ModelSerializer):
    user_lesson = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = ["id", "name", "user_lesson"]

    def get_user_lesson(self, obj):
        user_lessons = UserLesson.objects.filter(
            lesson=obj, user=self.context["request"].user
        ).first()
        serializer = UserLessonSerializer(user_lessons)
        return serializer.data


class MyDetailedLessonSerializer(serializers.ModelSerializer):
    files = FileSerializer(many=True)
    tasks = MyTaskSerializer(many=True)
    user_lesson = serializers.SerializerMethodField()
    previous_lesson_id = serializers.SerializerMethodField()
    next_lesson_id = serializers.SerializerMethodField()

    class Meta:
        model = Lesson
        fields = "__all__"

    def get_user_lesson(self, obj):
        user_lesson = UserLesson.objects.filter(
            lesson=obj, user=self.context["request"].user
        ).first()
        serializer = UserLessonSerializer(user_lesson)
        return serializer.data
    
    def get_previous_lesson_id(self, obj):
        # Fetch the lessons for the current chapter
        chapter_lessons = Lesson.objects.filter(chapter=obj.chapter).order_by('id')
        # Get the current lesson's index in the chapter
        current_index = list(chapter_lessons).index(obj)
        # Find the previous lesson, if it exists
        if current_index > 0:
            return chapter_lessons[current_index - 1].id
        return None  # No previous lesson

    def get_next_lesson_id(self, obj):
        # Fetch the lessons for the current chapter
        chapter_lessons = Lesson.objects.filter(chapter=obj.chapter).order_by('id')
        # Get the current lesson's index in the chapter
        current_index = list(chapter_lessons).index(obj)
        # Find the next lesson, if it exists
        if current_index < len(chapter_lessons) - 1:
            return chapter_lessons[current_index + 1].id
        return None  # No next lesson


class ChapterSerializer(serializers.ModelSerializer):
    lessons = OverviewLessonSerializer(many=True)

    class Meta:
        model = Chapter
        fields = "__all__"


class MyChapterSerializer(serializers.ModelSerializer):
    lessons = MyOverviewLessonSerializer(many=True)
    user_chapter = serializers.SerializerMethodField()

    class Meta:
        model = Chapter
        fields = "__all__"

    def get_user_chapter(self, obj):
        user_chapter = UserChapter.objects.filter(
            chapter=obj, user=self.context["request"].user
        ).first()  # Use first() to get the single instance or None
        if user_chapter:
            serializer = UserChapterSerializer(user_chapter)
            return serializer.data
        return None


class TrackSerializer(serializers.ModelSerializer):
    chapters = ChapterSerializer(many=True)
    pattern = PatternSerializer()

    class Meta:
        model = Track
        fields = "__all__"


class MyTrackSerializer(serializers.ModelSerializer):
    chapters = MyChapterSerializer(many=True)
    pattern = PatternSerializer()

    class Meta:
        model = Track
        fields = "__all__"


class UserCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserCourse
        fields = "__all__"


class UserChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserChapter
        fields = "__all__"


class UserLessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLesson
        fields = "__all__"


class UserTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTask
        fields = "__all__"


class BaseCourseSerializer(serializers.ModelSerializer):
    can_enroll = serializers.SerializerMethodField()
    has_enroll_limit_exceeded = serializers.SerializerMethodField()
    has_already_enrolled = serializers.SerializerMethodField()
    can_start = serializers.SerializerMethodField()
    has_start_limit_exceeded = serializers.SerializerMethodField()
    has_already_started = serializers.SerializerMethodField()
    button_text = serializers.SerializerMethodField()

    class Meta:
        abstract = True

    def get_user_subscription(self):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return request.user.subscriptions.filter(status="Current").first()
        return None

    def get_can_enroll(self, obj):
        user_subscription = self.get_user_subscription()
        if obj.is_paid:
            if user_subscription and user_subscription.subscription.level > 0:
                return True
            return False
        return True

    def get_has_enroll_limit_exceeded(self, obj):
        user_subscription = self.get_user_subscription()
        if user_subscription:
            if (
                user_subscription.enrolled_courses
                >= user_subscription.subscription.enroll_limit
            ):
                return True
        return False

    def get_has_already_enrolled(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return UserCourse.objects.filter(user=request.user, course=obj).exists()
        return False

    def get_can_start(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user_course = UserCourse.objects.filter(
                user=request.user, course=obj
            ).first()
            if user_course and user_course.status == "Enrolled":
                return True
        return False

    def get_has_start_limit_exceeded(self, obj):
        user_subscription = self.get_user_subscription()
        if user_subscription:
            if (
                user_subscription.started_courses
                >= user_subscription.subscription.start_limit
            ):
                return True
        return False

    def get_has_already_started(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return UserCourse.objects.filter(
                user=request.user, course=obj, status__in=["Started", "In Progress"]
            ).exists()
        return False

    def get_button_text(self, obj):
        if self.get_has_start_limit_exceeded(obj):
            return "Start Limit Exceeded" 
        if self.get_has_already_started(obj):
            return "Continue"
        if self.get_has_enroll_limit_exceeded(obj):
            return "Enroll Limit Exceeded"  
        if self.get_can_start(obj):
            return "Start"
        if self.get_can_enroll(obj) and not self.get_has_already_enrolled(obj):
            return "Enroll"
        return "Unavailable"

class OverviewCourseSerializer(BaseCourseSerializer):
    tags = TagSerializer(many=True)
    category = CategorySerializer()

    class Meta:
        model = Course
        fields = [
            "id",
            "main_category",
            "name",
            "short_description",
            "cover_image",
            "is_paid",
            "category",
            "tags",
            "can_enroll",
            "has_enroll_limit_exceeded",
            "has_already_enrolled",
            "can_start",
            "has_start_limit_exceeded",
            "has_already_started",
            "button_text"
        ]


class MyOverviewCourseSerializer(BaseCourseSerializer):
    tags = TagSerializer(many=True)
    category = CategorySerializer()
    user_course = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "user_course",
            "main_category",
            "name",
            "short_description",
            "cover_image",
            "is_paid",
            "category",
            "tags",
            "can_enroll",
            "has_enroll_limit_exceeded",
            "has_already_enrolled",
            "can_start",
            "has_start_limit_exceeded",
            "has_already_started",
            "button_text"
        ]

    def get_user_course(self, obj):
        user_course = UserCourse.objects.filter(
            course=obj, user=self.context["request"].user
        ).first()
        if user_course:
            serializer = UserCourseSerializer(user_course)
            return serializer.data
        return None


class DetailedCourseSerializer(BaseCourseSerializer):
    tags = TagSerializer(many=True)
    category = CategorySerializer()
    tracks = TrackSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = "__all__"


class MyDetailedCourseSerializer(BaseCourseSerializer):
    tags = TagSerializer(many=True)
    category = CategorySerializer()
    tracks = MyTrackSerializer(many=True, read_only=True)
    user_course = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = "__all__"

    def get_user_course(self, obj):
        user_course = UserCourse.objects.filter(
            course=obj, user=self.context["request"].user
        ).first()
        if user_course:
            serializer = UserCourseSerializer(user_course)
            return serializer.data
        return None
