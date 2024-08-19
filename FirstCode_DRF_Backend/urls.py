from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Importing views with aliases
from course import views as course_views
from liveclass import views as liveclass_views
from subscription import views as subscription_views
from user import views as user_views

# Initialize the router
router = DefaultRouter()

# Registering viewsets from the course app
router.register(r'categories', course_views.CategoryViewSet)
router.register(r'tags', course_views.TagViewSet)
router.register(r'courses', course_views.CourseViewSet)
router.register(r'tracks', course_views.TrackViewSet)
router.register(r'chapters', course_views.ChapterViewSet)
router.register(r'lessons', course_views.LessonViewSet)
router.register(r'files', course_views.FileViewSet)
router.register(r'tasks', course_views.TaskViewSet)
router.register(r'user-courses', course_views.UserCourseViewSet)
router.register(r'user-chapters', course_views.UserChapterViewSet)
router.register(r'user-lessons', course_views.UserLessonViewSet)
router.register(r'user-tasks', course_views.UserTaskViewSet)

# Registering viewsets from the liveclass app
router.register(r'live-classes', liveclass_views.LiveClassViewSet)
router.register(r'user-live-classes', liveclass_views.UserLiveClassViewSet)

# Registering viewsets from the subscription app
router.register(r'list-subscriptions', subscription_views.ListSubscriptionViewSet, basename='list-subscriptions')
router.register(r'subscription', subscription_views.UserSubscriptionViewSet, basename='subscription')

# Registering viewsets from the user app
router.register(r'signup', user_views.Signup, basename='signup')
router.register(r'assign-pattern', user_views.PatternAssignmentViewSet, basename='assign-pattern')
router.register(r'update-name', user_views.UserNameUpdateViewSet, basename='update-name')
router.register(r'delete-account', user_views.UserDeleteViewSet, basename='delete-account')

# URL patterns
urlpatterns = [
    path("auth/", user_views.Signin.as_view()),
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
