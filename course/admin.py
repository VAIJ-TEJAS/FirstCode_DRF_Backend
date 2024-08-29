import nested_admin
from django.contrib import admin
from .models import (
    Category, Tag, Course, Track, Chapter, Lesson, File, Task,
    UserCourse, UserChapter, UserLesson, UserTask
)

# Inlines
class FileInline(nested_admin.NestedTabularInline):
    model = File
    extra = 1

class TaskInline(nested_admin.NestedTabularInline):
    model = Task
    extra = 1

class LessonInline(nested_admin.NestedTabularInline):
    model = Lesson
    extra = 1
    inlines = [FileInline, TaskInline]

class ChapterInline(nested_admin.NestedTabularInline):
    model = Chapter
    extra = 1
    inlines = [LessonInline]

class TrackInline(nested_admin.NestedTabularInline):
    model = Track
    extra = 1
    inlines = [ChapterInline]

class UserCourseInline(nested_admin.NestedTabularInline):
    model = UserCourse
    extra = 1

# Admin Classes
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Course)
class CourseAdmin(nested_admin.NestedModelAdmin):
    list_display = ['name', 'main_category', 'category', 'is_paid']
    inlines = [TrackInline]

@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display = ['name', 'course', 'pattern']

@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = ['name', 'track']

@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ['name', 'chapter', 'playground_type']

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['lesson', 'file']

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'lesson']

@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    list_display = ['user', 'course', 'status', 'completed_chapters', 'created_at']
    list_filter = ['status']
    search_fields = ['user__username', 'course__name']

@admin.register(UserChapter)
class UserChapterAdmin(admin.ModelAdmin):
    list_display = ['user', 'chapter', 'status', 'completed_lessons', 'created_at']

@admin.register(UserLesson)
class UserLessonAdmin(admin.ModelAdmin):
    list_display = ['user', 'lesson', 'status', 'completed_tasks', 'created_at']

@admin.register(UserTask)
class UserTaskAdmin(admin.ModelAdmin):
    list_display = ['user', 'task', 'created_at']
