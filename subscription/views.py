from datetime import datetime, timedelta
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from order.models import Order
from user.models import UserProfile
from .models import Subscription, UserSubscription
from .serializers import SubscriptionSerializer, UserSubscriptionSerializer

import razorpay
import time
import os
import hmac
import hashlib
import json

client = razorpay.Client(auth=(os.getenv("KEY_ID"), os.getenv("KEY_SECRET")))


class ListSubscriptionViewSet(viewsets.ModelViewSet):
    serializer_class = SubscriptionSerializer
    http_method_names = ["get"]

    def get_queryset(self):
        # Exclude subscriptions with level 0
        return Subscription.objects.filter(level__gt=0)


class UserSubscriptionViewSet(viewsets.ModelViewSet):
    queryset = UserSubscription.objects.all()
    serializer_class = UserSubscriptionSerializer

    @action(detail=False, methods=["post"], url_path="create-order")
    def create_order(self, request, *args, **kwargs):
        subscription_id = request.data.get("subscription_id")
        subscription_type = request.data.get("subscription_type")

        if subscription_type not in ["NEW", "RENEW"]:
            return Response(
                {"error": "Invalid subscription type."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        subscription = Subscription.objects.get(id=subscription_id)

        if not subscription:
            return Response(
                {"error": "Subscription not found."}, status=status.HTTP_404_NOT_FOUND
            )

        # Static amount of 1000 INR for all subscription payments
        subscription_amount = (
            subscription.price * 100
        )  # Razorpay expects amount in paise

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

        # Create the Order object
        Order.objects.create(
            order_id=razorpay_order["id"],
            user=request.user,
            subscription=subscription,
            subscription_type=subscription_type,
            completed=False,  # Default value
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


class PaymentWebhookViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["post"], url_path="payment-success")
    def payment_successful_webhook(self, request, *args, **kwargs):
        # Debugging headers, query params, and payload
        print("Headers:", request.headers)
        print("Query Params:", request.query_params)
        print("Payload:", request.data)

        # Get Razorpay signature from the headers
        signature = request.headers.get("X-Razorpay-Signature")
        if not signature:
            return Response({"error": "Signature missing"}, status=status.HTTP_400_BAD_REQUEST)

        # Verify the signature using the secret
        webhook_secret = os.getenv("WEBHOOK_SECRET")
        payload = json.dumps(request.data, separators=(",", ":"))  # Convert payload to JSON string
        expected_signature = hmac.new(
            webhook_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Compare computed signature with the one from the header
        if not hmac.compare_digest(expected_signature, signature):
            return Response({"error": "Invalid signature"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract the order_id from the payload
        payment_data = request.data.get("payload", {}).get("payment", {}).get("entity", {})
        order_id = payment_data.get("order_id")

        if not order_id:
            return Response({"error": "Order ID missing from payload"}, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the Order object
        try:
            order = Order.objects.get(order_id=order_id)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

        # Check if the payment status is 'captured'
        if payment_data.get("status") != "captured":
            return Response({"error": "Payment not captured"}, status=status.HTTP_400_BAD_REQUEST)

        # Get the user from the order
        user = order.user

        # Get subscription details from the order
        subscription_id = order.subscription.id
        subscription_type = order.subscription_type

        # Perform actions based on the subscription type
        if subscription_type == "NEW":
            response = self.create_new_subscription(user, subscription_id, payment_data)
        elif subscription_type == "RENEW":
            response = self.renew_subscription(user, subscription_id, payment_data)
        else:
            return Response({"error": "Invalid subscription type"}, status=status.HTTP_400_BAD_REQUEST)

        # Mark the order as completed
        order.completed = True
        order.save()

        return response

    def create_new_subscription(self, user, subscription_id, payment_data):
        subscription = Subscription.objects.get(id=subscription_id)
        today = timezone.now().date()
        user_profile, _ = UserProfile.objects.get_or_create(user=user)
        current_subscription = user_profile.current_subscription

        # Determine start date and handle existing subscription if necessary
        if current_subscription:
            start_date = timezone.make_aware(
                datetime.combine(
                    current_subscription.subscription_end_date + timedelta(days=1),
                    datetime.min.time(),
                )
            )
            current_subscription.status = "Expired"
            current_subscription.save()
        else:
            start_date = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        # Calculate end date based on the subscription validity
        end_date = start_date + timedelta(days=subscription.validity)

        # Create a new UserSubscription
        user_subscription = UserSubscription.objects.create(
            user=user,
            subscription=subscription,
            subscription_start_date=start_date,
            subscription_end_date=end_date,
            status="Current",
            payment=payment_data  # Store the payment data in the subscription
        )

        # Update the user's profile with the new subscription
        user_profile.current_subscription = user_subscription
        user_profile.save()

        serializer = UserSubscriptionSerializer(user_subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def renew_subscription(self, user, subscription_id, payment_data):
        subscription = Subscription.objects.get(id=subscription_id)
        user_profile, _ = UserProfile.objects.get_or_create(user=user)
        current_subscription = user_profile.current_subscription
        today = timezone.now().date()

        # Calculate the start date based on the current subscription
        if current_subscription:
            current_end_date = current_subscription.subscription_end_date.date()
            start_date = max(today, current_end_date + timedelta(days=1))
            start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        else:
            start_datetime = timezone.make_aware(datetime.combine(today, datetime.min.time()))

        # Calculate the end date based on subscription validity
        end_datetime = start_datetime + timedelta(days=subscription.validity)

        # Determine the status and handle renewal of current subscription
        if current_subscription and current_subscription.subscription_end_date.date() >= today:
            status_new_subscription = "Upcoming"
            current_subscription.renewed = True
            current_subscription.save()
            assign_to_profile = False
        else:
            status_new_subscription = "Current"
            assign_to_profile = True

        # Create the renewed subscription
        user_subscription = UserSubscription.objects.create(
            user=user,
            subscription=subscription,
            subscription_start_date=start_datetime,
            subscription_end_date=end_datetime,
            status=status_new_subscription,
            payment=payment_data  # Store payment data
        )

        # Assign the renewed subscription to the user profile if needed
        if assign_to_profile:
            user_profile.current_subscription = user_subscription
            user_profile.save()

        serializer = UserSubscriptionSerializer(user_subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)