from datetime import datetime
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from user.models import UserProfile
from .models import Subscription, UserSubscription
from .serializers import ListSubscriptionSerializer, UserSubscriptionSerializer

import razorpay
import time
import os

client = razorpay.Client(auth=(os.getenv("KEY_ID"), os.getenv("KEY_SECRET")))

class ListSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = Subscription.objects.all()
    serializer_class = ListSubscriptionSerializer
    http_method_names = ["get"]


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer

    @action(detail=False, methods=["post"], url_path="calculate")
    def calc_payment_amount(self, request, *args, **kwargs):
        # Static amount of 1000 INR for all subscription payments
        subscription_amount = 1000 * 100  # Razorpay expects amount in paise

        # Create an order with Razorpay
        order_currency = "INR"
        order_receipt = f"receipt_{int(time.time())}"
        notes = {"user_id": request.user.id}  # Add any notes if needed

        razorpay_order = client.order.create(
            dict(
                amount=subscription_amount,  # amount in paise
                currency=order_currency,
                receipt=order_receipt,
                notes=notes,
            )
        )

        # Return the Razorpay order ID and other details
        return Response(
            {
                "order_id": razorpay_order["id"],
                "razorpay_key_id": os.getenv("KEY_ID"),
                "amount": subscription_amount,  # returning amount in paise
                "currency": order_currency,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], url_path="new")
    def create_new_subscription(self, request, *args, **kwargs):
        subscription_id = request.data.get("subscription_id")
        subscription = self._get_subscription(subscription_id)

        if not subscription:
            return Response(
                {"error": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND
            )

        today = timezone.now().date()
        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        current_subscription = user_profile.current_subscription

        if current_subscription:
            start_date = timezone.make_aware(
                datetime.combine(
                    current_subscription.subscription_end_date
                    + timezone.timedelta(days=1),
                    datetime.min.time(),
                )
            )
            current_subscription.status = "Expired"
            current_subscription.save()
        else:
            start_date = timezone.make_aware(
                datetime.combine(today, datetime.min.time())
            )

        end_date = start_date + timezone.timedelta(days=subscription.validity)

        user_subscription = UserSubscription.objects.create(
            user=request.user,
            subscription=subscription,
            amount=subscription.price,
            payment_id=request.data.get("payment_id", None),
            order_id=request.data.get("order_id", None),
            signature=request.data.get("signature", None),
            payment_status=request.data.get("payment_status", None),
            payment_method=request.data.get("payment_method", None),
            subscription_start_date=start_date,
            subscription_end_date=end_date,
            status="Current",
        )

        user_profile.current_subscription = user_subscription
        user_profile.save()

        serializer = self.get_serializer(user_subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="renew")
    def renew_subscription(self, request, *args, **kwargs):
        subscription_id = request.data.get("subscription_id")
        subscription = self._get_subscription(subscription_id)

        if not subscription:
            return Response(
                {"error": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND
            )

        user_profile, _ = UserProfile.objects.get_or_create(user=request.user)
        current_subscription = user_profile.current_subscription

        today = timezone.now().date()  # Get current date only

        if current_subscription:
            # Compare dates only
            current_end_date = current_subscription.subscription_end_date.date()
            # The new start date is the maximum of today's date or the current subscription's end date + 1 day
            start_date = max(today, current_end_date + timezone.timedelta(days=1))
            start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        else:
            # If there's no current subscription, start date is today
            start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        end_datetime = start_datetime + timezone.timedelta(days=subscription.validity)

        # Determine the status for the new subscription
        if current_subscription:
            if current_subscription.subscription_end_date.date() >= today:
                # If current subscription is still valid or ends today, mark new subscription as 'Upcoming'
                status_new_subscription = "Upcoming"
                current_subscription.renewed = True
                current_subscription.save()

                # Assign the new subscription to the profile only if the current one was expired
                assign_to_profile = False
            else:
                # If the current subscription is expired, mark new subscription as 'Current'
                status_new_subscription = "Current"
                assign_to_profile = True
        else:
            # No current subscription means this new one is 'Current'
            status_new_subscription = "Current"
            assign_to_profile = True

        # Create the new UserSubscription object
        user_subscription = UserSubscription.objects.create(
            user=request.user,
            subscription=subscription,
            amount=subscription.price,
            payment_id=request.data.get("payment_id", None),
            order_id=request.data.get("order_id", None),
            signature=request.data.get("signature", None),
            payment_status=request.data.get("payment_status", None),
            payment_method=request.data.get("payment_method", None),
            subscription_start_date=start_datetime,
            subscription_end_date=end_datetime,
            status=status_new_subscription,
        )

        # Update user profile with the new subscription only if applicable
        if assign_to_profile:
            user_profile.current_subscription = user_subscription
            user_profile.save()

        serializer = self.get_serializer(user_subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def _get_subscription(self, subscription_id):
        try:
            return Subscription.objects.get(id=subscription_id)
        except Subscription.DoesNotExist:
            return None

class PaymentWebhookViewSet(viewsets.ViewSet):

    # Allow any request to this endpoint
    @permission_classes([AllowAny])
    @action(detail=False, methods=["post"], url_path="payment-success")
    def payment_successful_webhook(self, request, *args, **kwargs):
        # Print the incoming payload for debugging (remove in production)
        print(request.data)

        # Process the payment data here
        # You can verify the signature from Razorpay and process accordingly
        
        # Respond with a simple acknowledgment
        return Response({"status": "received"}, status=status.HTTP_200_OK)