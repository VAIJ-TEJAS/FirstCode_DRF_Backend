from django.utils import timezone
from django.utils.timezone import now, timedelta
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from subscription.models import UserSubscription
from user.models import User, UserProfile
from user.serializers import UserSerializer
from utils.email_dynamic_sender import send_email_with_dynamic_sender
from .models import OTP
import random


class GenerateOTPRegister(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if a user with the given email already exists
        if User.objects.filter(email=email).exists():
            # Return an error response if user already exists
            return Response(
                {"error": "User with this email already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate a 6-digit OTP
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        # Set OTP expiration time (e.g., 10 minutes from now)
        expires_at = now() + timedelta(minutes=10)

        # Create OTP object
        OTP.objects.create(email=email, code=otp_code, expires_at=expires_at)

        # Send OTP via email
        send_email_with_dynamic_sender(
            subject="Your OTP",
            message=f"Your OTP is {otp_code}. It will expire in 10 minutes.",
            from_email="firstcode.in@tejasvaij.com",
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent to email."}, status=status.HTTP_200_OK)


class GenerateOTPLogin(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("email")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Authenticate user
        user = authenticate(username=username, password=password)
        if not user:
            return Response(
                {"error": "Invalid username or password"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Check if the user has an email associated
        if not user.email:
            return Response(
                {"error": "User does not have an associated email"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Generate a 6-digit OTP
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        # Set OTP expiration time (e.g., 10 minutes from now)
        expires_at = now() + timedelta(minutes=10)

        # Create OTP object
        OTP.objects.create(email=user.email, code=otp_code, expires_at=expires_at)

        # Send OTP via email
        send_email_with_dynamic_sender(
            subject="Your Login OTP",
            message=f"Your OTP is {otp_code}. It will expire in 10 minutes.",
            from_email="firstcode.in@tejasvaij.com",
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent to email."}, status=status.HTTP_200_OK)


class GenerateOTPResetPassword(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if a user with the given email exists
        if not User.objects.filter(email=email).exists():
            # Return an error response if no user is found
            return Response(
                {"error": "No user found with this email"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate a 6-digit OTP
        otp_code = "".join([str(random.randint(0, 9)) for _ in range(6)])

        # Set OTP expiration time (e.g., 10 minutes from now)
        expires_at = now() + timedelta(minutes=10)

        # Create OTP object
        OTP.objects.create(email=email, code=otp_code, expires_at=expires_at)

        # Send OTP via email
        send_email_with_dynamic_sender(
            subject="Your OTP",
            message=f"Your OTP is {otp_code}. It will expire in 10 minutes.",
            from_email="firstcode.in@tejasvaij.com",
            recipient_list=[email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent to email."}, status=status.HTTP_200_OK)


class VerifyOTPRegister(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        otp_code = request.data.get("otp")
        user_data = request.data.get("user_data")

        if not email or not otp_code or not user_data:
            return Response(
                {"error": "Email, OTP, and user data are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Attempt to retrieve the relevant OTP object
        try:
            otp_obj = OTP.objects.get(email=email, code=otp_code, is_used=False)
        except OTP.DoesNotExist:
            return Response(
                {"error": "Invalid OTP or email"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the OTP is expired
        if otp_obj.expires_at < now():
            return Response(
                {"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Mark OTP as used (to prevent reuse)
        otp_obj.is_used = True
        otp_obj.save()

        # Create the user since OTP is valid
        user_data["email"] = email  # Ensure email is included in user_data
        if "password" in user_data:
            user_data["password"] = make_password(user_data["password"])

        user_serializer = UserSerializer(data=user_data)
        if user_serializer.is_valid():
            user = user_serializer.save()
            token = Token.objects.create(user=user)
            
            # Create UserProfile for the user
            UserProfile.objects.create(user=user)

            # Fetch the subscription with level 0
            try:
                default_subscription = UserSubscription.objects.get(level=0)
            except UserSubscription.DoesNotExist:
                return Response({"error": "Default subscription not found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Assign the subscription to the user
            UserSubscription.objects.create(
                user=user,
                subscription=default_subscription.subscription,
                amount=default_subscription.subscription.price,
                subscription_start_date=timezone.now(),
                subscription_end_date=timezone.now() + timedelta(days=default_subscription.subscription.validity),
                status="Current",
            )

            return Response(
                {"token": token.key, "user": user_serializer.data},
                status=status.HTTP_200_OK,
            )
        else:
            return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VerifyOTPLogin(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        otp_code = request.data.get("otp")

        if not email or not otp_code:
            return Response(
                {"error": "Email and OTP are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Attempt to retrieve the OTP object
        try:
            otp_obj = OTP.objects.get(email=email, code=otp_code, is_used=False)
        except OTP.DoesNotExist:
            return Response(
                {"error": "Invalid OTP or email"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if the OTP is expired
        if otp_obj.expires_at < now():
            return Response(
                {"error": "OTP has expired"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Mark OTP as used
        otp_obj.is_used = True
        otp_obj.save()

        # Fetch the user by email
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        # Update the last login field
        user.last_login = timezone.now()
        user.save()

        # Create or fetch token
        old_token = Token.objects.get(user=user)
        # Delete the old token and create a new one
        # old_token.delete()
        # new_token = Token.objects.create(user=user)

        # Serialize the user object
        user_serializer = UserSerializer(user)

        return Response(
            {"token": old_token.key, "user": user_serializer.data},
            status=status.HTTP_200_OK,
        )


class VertifyOTPResetPassword(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        otp_code = request.data.get("otp")
        new_password = request.data.get("new_password")

        if not all([email, otp_code, new_password]):
            return Response(
                {"error": "Email, OTP, and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate OTP
        try:
            otp_obj = OTP.objects.get(email=email, code=otp_code, expires_at__gt=now())
        except OTP.DoesNotExist:
            return Response(
                {"error": "Invalid or expired OTP."}, status=status.HTTP_400_BAD_REQUEST
            )

        # Update user's password
        user = User.objects.get(email=email)
        user.password = make_password(new_password)
        user.save()

        # Optionally, delete the OTP after use
        otp_obj.delete()

        return Response(
            {"message": "Password reset successfully."}, status=status.HTTP_200_OK
        )
