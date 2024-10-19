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
        subscription_end_date__lt=today,
        status='Current'
    )

    for subscription in expired_subscriptions:
        # Store user email for sending notifications later
        user_email = subscription.user.email

        subscription.status = 'Expired'
        subscription.save()

        if not subscription.renewed:
            # Send email notification about the expired subscription
            subject = "Subscription Expired Notification"
            message = (
                f"Dear {subscription.user.username},\n\n"
                f"Your subscription '{subscription.subscription.name}' has expired as of {subscription.subscription_end_date.date()}."
                "\nWe noticed that you have not renewed your subscription. "
                "Please consider renewing to continue enjoying our services.\n\n"
                "Best regards,\nYour Company Name"
            )
            from_email = "noreply@firstcode.in"  # Use a default sender
            send_email_with_dynamic_sender(subject, message, from_email, [user_email])

    # Promote upcoming subscriptions to current
    upcoming_subscriptions = UserSubscription.objects.filter(
        subscription_start_date__lte=today,
        status='Upcoming'
    )

    for subscription in upcoming_subscriptions:
        subscription.status = 'Current'
        subscription.save()

        user_profile, _ = UserProfile.objects.get_or_create(user=subscription.user)
        user_profile.current_subscription = subscription
        user_profile.save()

        # Send email notification about the renewal of the subscription
        subject = "Subscription Renewal Notification"
        message = (
            f"Dear {subscription.user.username},\n\n"
            f"Your subscription '{subscription.subscription.name}' has been renewed successfully. "
            f"It is now active until {subscription.subscription_end_date.date()}.\n\n"
            "Thank you for your continued support!\n\n"
            "Best regards,\nYour Company Name"
        )
        send_email_with_dynamic_sender(subject, message, from_email, [user_email])


@shared_task
def notify_users_about_subscription_expiration():
    today = timezone.now()
    
    # Define the notification days (in days remaining)
    notification_days = [30, 15, 7, 3, 2, 1]

    for days in notification_days:
        expiration_date = today + timezone.timedelta(days=days)
        
        # Get subscriptions that expire on this date and are not renewed
        expiring_subscriptions = UserSubscription.objects.filter(
            subscription_end_date=expiration_date,
            status='Current',
            renewed=False
        )

        for subscription in expiring_subscriptions:
            user_email = subscription.user.email
            subject = f"Subscription Expiration Reminder"
            message = (
                f"Dear {subscription.user.username},\n\n"
                f"Your subscription '{subscription.subscription.name}' will expire on {subscription.subscription_end_date.date()}."
                f"\nPlease consider renewing your subscription to continue enjoying our services.\n\n"
                "Best regards,\nYour Company Name"
            )
            from_email = "noreply@firstcode.in"  # Use a default sender
            
            send_email_with_dynamic_sender(subject, message, from_email, [user_email])