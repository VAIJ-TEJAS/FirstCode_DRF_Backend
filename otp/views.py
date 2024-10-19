from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string
from rest_framework import viewsets
from django.utils.timezone import now, timedelta
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from subscription.models import Subscription, UserSubscription
from user.models import User, UserProfile
from user.serializers import UserSerializer
from utils.email_dynamic_sender import send_email_with_dynamic_sender
from .models import OTP, PasswordResetToken
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
            from_email="noreply@firstcode.in",
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
            from_email="noreply@firstcode.in",
            recipient_list=[user.email],
            fail_silently=False,
        )

        return Response({"message": "OTP sent to email."}, status=status.HTTP_200_OK)


class SendPasswordResetLink(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        if not email:
            return Response(
                {"error": "Email is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        # Check if a user with the given email exists
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "No user found with this email"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Generate a token (can be anything unique)
        token = get_random_string(30)
        expires_at = now() + timedelta(hours=1)  # Link valid for 1 hour

        # Create a new password reset token
        PasswordResetToken.objects.create(
            email=email, token=token, expires_at=expires_at, is_used=False
        )

        # Build the password reset link
        # Change this to use localhost:3000
        reset_url = f"https://first-code-react-frontend.vercel.app/auth/reset-password/?email={email}&token={token}"

        # Send the reset password email
        send_email_with_dynamic_sender(
            subject="Password Reset Link",
            message=f"Click on the link to reset your password: {reset_url}",
            from_email="noreply@firstcode.in",
            recipient_list=[email],
            fail_silently=False,
        )

        return Response(
            {"message": "Password reset link sent to email."}, status=status.HTTP_200_OK
        )


class VerifyOTPRegister(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @transaction.atomic
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

            # Fetch the subscription with level 0
            try:
                default_subscription = Subscription.objects.get(level=0)
            except Subscription.DoesNotExist:
                return Response(
                    {"error": "Default subscription not found"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            # Assign the subscription to the user
            new_subscription = UserSubscription.objects.create(
                user=user,
                subscription=default_subscription,
                subscription_start_date=timezone.now(),
                subscription_end_date=timezone.now()
                + timedelta(days=default_subscription.validity),
                status="Current",
            )

            # Create UserProfile for the user
            UserProfile.objects.create(user=user, current_subscription=new_subscription)

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
        old_token.delete()
        new_token = Token.objects.create(user=user)

        # Serialize the user object
        user_serializer = UserSerializer(user)

        return Response(
            {"token": new_token.key, "user": user_serializer.data},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirm(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get("email")
        token = request.data.get("token")
        new_password = request.data.get("new_password")

        if not all([email, token, new_password]):
            return Response(
                {"error": "Email, token, and new password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate the token
        try:
            reset_token = PasswordResetToken.objects.get(
                email=email, token=token, expires_at__gt=now(), is_used=False
            )
        except PasswordResetToken.DoesNotExist:
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Update the user's password
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "User not found"}, status=status.HTTP_404_NOT_FOUND
            )

        user.password = make_password(new_password)
        user.save()

        # Mark the token as used
        reset_token.is_used = True
        reset_token.save()

        return Response(
            {"message": "Password reset successfully."}, status=status.HTTP_200_OK
        )

class CurrentUserViewSet(APIView):
    permission_classes = [IsAuthenticated] 

    def post(self, request, *args, **kwargs):
        user = request.user  
        user_serializer = UserSerializer(user)  
        
        # Create or fetch token
        old_token, created = Token.objects.get_or_create(user=user)
        
        # If the token already exists, delete it and create a new one
        if not created:
            old_token.delete()
            new_token = Token.objects.create(user=user)
        else:
            new_token = old_token  # Use the newly created token if it was created

        # Prepare the response as a dictionary
        return Response(
            {
                "token": new_token.key,  # Return the token
                "user": user_serializer.data,  # Return the serialized user data
            },
            status=status.HTTP_200_OK,
        )