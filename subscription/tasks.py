from celery import shared_task
from django.utils import timezone
from user.models import UserProfile
from .models import UserSubscription
from utils.email_dynamic_sender import send_email_with_dynamic_sender


@shared_task
def update_subscriptions():
    today = timezone.now()

    # Update expired subscriptions
    expired_subscriptions = UserSubscription.objects.filter(
        subscription_end_date__lt=today, status="Current"
    )

    for user_subscription in expired_subscriptions:
        # Store user email for sending notifications later
        user_email = user_subscription.user.email

        user_subscription.status = "Expired"
        user_subscription.save()

        if not user_subscription.renewed:
            # Send email notification about the expired subscription
            # Context for rendering the email template
            context = {"user_subscription": user_subscription}

            # Send OTP via email
            send_email_with_dynamic_sender(
                subject="Subscription Expired Notification",
                message=(
                    f"Dear {user_subscription.user.username},\n\n"
                    f"Your subscription '{user_subscription.subscription.name}' has expired as of {user_subscription.subscription_end_date.date()}."
                    "\nWe noticed that you have not renewed your subscription. "
                    "Please consider renewing to continue enjoying our services.\n\n"
                    "Best regards,\nYour Company Name"
                ),
                from_email="noreply@firstcode.in",
                context=context,
                template="expired_subscription.html",
                recipient_list=[user_subscription.user.email],
                fail_silently=False,
            )

    # Promote upcoming subscriptions to current
    upcoming_subscriptions = UserSubscription.objects.filter(
        subscription_start_date__lte=today, status="Upcoming"
    )

    for user_subscription in upcoming_subscriptions:
        user_subscription.status = "Current"
        user_subscription.save()

        user_profile, _ = UserProfile.objects.get_or_create(user=user_subscription.user)
        user_profile.current_subscription = user_subscription
        user_profile.save()


@shared_task
def notify_users_about_subscription_expiration():
    today = timezone.now()

    # Define the notification days (in days remaining)
    notification_days = [30, 15, 7, 3, 2, 1]

    for days in notification_days:
        expiration_date = today + timezone.timedelta(days=days)

        # Get subscriptions that expire on this date and are not renewed
        expiring_subscriptions = UserSubscription.objects.filter(
            subscription_end_date=expiration_date, status="Current", renewed=False
        )

        for user_subscription in expiring_subscriptions:
            # Context for rendering the email template
            context = {
                'days': days,
                'end_date': user_subscription.subscription_end_date,
            }

            # Send OTP via email
            send_email_with_dynamic_sender(
                subject="Subscription Expiration Reminder",
                message=(
                    f"Dear {user_subscription.user.username},\n\n"
                    f"Your subscription '{user_subscription.subscription.name}' will expire on {user_subscription.subscription_end_date.date()}."
                    f"\nPlease consider renewing your subscription to continue enjoying our services.\n\n"
                    "Best regards,\nYour Company Name"
                ),
                from_email="noreply@firstcode.in",
                context=context,
                template="alert_expiry_subscription.html",
                recipient_list=[user_subscription.user.email],
                fail_silently=False,
            )
