from django.contrib import admin
from django.conf import settings
from django.urls import path, include
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter

# Importing views with aliases
from course import views as course_views
from liveclass import views as liveclass_views
from otp.views import GenerateOTPLogin, GenerateOTPRegister, PasswordResetConfirm, SendPasswordResetLink, VerifyOTPLogin, VerifyOTPRegister, CurrentUserViewSet
from subscription import views as subscription_views
from user import views as user_views
from quote import views as quote_views
from course.planner.views import LearningPathPlannerAPIView

# Initialize the router
router = DefaultRouter()

# Registering viewsets from the course app
router.register(r'categories', course_views.CategoryViewSet, basename='categories')
router.register(r'courses', course_views.CourseViewSet, basename='courses')
router.register(r'my-courses', course_views.MyCourseViewSet, basename='my-courses')
router.register(r'my-lessons', course_views.MyLessonViewSet, basename='lessons')
router.register(r'user-courses', course_views.UserCourseViewSet, basename='user-courses')
router.register(r'user-tasks', course_views.UserTaskViewSet, basename='user-tasks')
router.register(r'user-course-certificates', course_views.UserCourseCertificateViewSet, basename='user-course-certificates')
router.register(r'inactive-courses', course_views.InactiveCoursesViewSet, basename='inactive-courses')

# Registering viewsets from the liveclass app
router.register(r'liveclasses', liveclass_views.LiveClassViewSet, basename='liveclasses')
router.register(r'my-liveclasses', liveclass_views.MyLiveClassViewSet, basename='my-liveclasses')
router.register(r'user-liveclasses', liveclass_views.UserLiveClassViewSet, basename='user-liveclasses')

# Registering viewsets from the subscription app
router.register(r'list-subscriptions', subscription_views.ListSubscriptionViewSet, basename='list-subscriptions')
router.register(r'subscription', subscription_views.UserSubscriptionViewSet, basename='subscription')

# Registering viewsets from the user app
router.register(r'assign-pattern', user_views.PatternAssignmentViewSet, basename='assign-pattern')
router.register(r'update-name', user_views.UserNameUpdateViewSet, basename='update-name')
router.register(r'delete-account', user_views.UserDeleteViewSet, basename='delete-account')
router.register(r'learning-progress', user_views.LearningProgressGraphViewSet, basename='learning-progress')
router.register(r'monthly-progress', user_views.MonthlyProgressViewSet, basename='monthly-progress')
router.register(r'streak', user_views.StreakViewSet, basename='streak')
router.register(r'piechart-stats', user_views.PieChartViewSet, basename='piechart-stats')
router.register(r'events-stats', user_views.EventViewSet, basename='events-stats')
router.register(r'leftcourses-stats', user_views.LeftCoursesViewSet, basename='leftcourses-stats')
router.register(r'latest-courses-classes', user_views.LatestCoursesAndClassesViewSet, basename='latest-courses-classes')

# Register the PaymentWebhookViewSet
router.register(r'webhook', subscription_views.PaymentWebhookViewSet, basename='payment-webhook')

# URL patterns
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include(router.urls)),
    path('learning-path/planner/', LearningPathPlannerAPIView.as_view(), name='learning-path-planner'),
    path('google-complete/', user_views.google_complete, name='google_complete'),
    path('generate-otp-register/', GenerateOTPRegister.as_view(), name='generate-otp-register'),
    path('verify-otp/', VerifyOTPRegister.as_view(), name='verify-otp'),
    path('generate-otp-login/', GenerateOTPLogin.as_view(), name='generate-otp-login'),
    path('verify-otp-login/', VerifyOTPLogin.as_view(), name='verify-otp-login'),
    path('reset_password_confirm/', SendPasswordResetLink.as_view(), name='reset_password_confirm'),
    path('reset-password-confirmed/', PasswordResetConfirm.as_view(), name='reset-password-confirmed'),
    path('personalised-quote/', quote_views.RandomPersonalisedQuoteView.as_view(), name='personalised-quote'),
    path('current-user/', CurrentUserViewSet.as_view(), name='current-user'),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
