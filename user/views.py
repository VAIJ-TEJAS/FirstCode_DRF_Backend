from datetime import timedelta
from django.utils import timezone
from .models import Pattern, UserProfile
from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.views import ObtainAuthToken
from .serializers import UserProfileSerializer, UserSerializer

class Signup(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    http_method_names = ["post"]

    def create(self, request):
        serializer = UserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.create_user(**serializer.validated_data)
        token = Token.objects.create(user=user)

        # Create UserProfile for the user
        UserProfile.objects.create(user=user)

        # Serialize the user object
        user_serializer = UserSerializer(token.user)
        serialized_user = user_serializer.data

        return Response({"token": token.key, "user": serialized_user})


class Signin(ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        response = super(Signin, self).post(request, *args, **kwargs)
        old_token = response.data["token"]

        # Get the user associated with this token
        old_token = Token.objects.get(key=old_token)
        user = old_token.user

        # Update the last_login field
        user.last_login = timezone.now()
        user.save()

        # Delete the old token and create a new one
        # old_token.delete()
        # new_token = Token.objects.create(user=user)

        # Serialize the user object
        user_serializer = UserSerializer(user)
        serialized_user = user_serializer.data

        return Response({"token": old_token.key, "user": serialized_user})


class UserNameUpdateViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    http_method_names = ["post"]

    def create(self, request, *args, **kwargs):
        user = self.request.user
        profile = UserProfile.objects.get(user=user)

        # Check if the user has changed their name in the last 30 days
        if profile.last_name_change:
            one_month_ago = timezone.now() - timedelta(days=30)
            if profile.last_name_change > one_month_ago:
                return Response(
                    {"detail": "You can only change your name once every 30 days."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Proceed to update the user's name
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Update the last_name_change field in UserProfile
        profile.last_name_change = timezone.now()
        profile.save()

        return Response(serializer.data)


class UserDeleteViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    http_method_names = ["post"]

    def create(self, request, *args, **kwargs):
        user = self.request.user
        
        # Ensure UserProfile is saved
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Delete the associated UserProfile
        profile.delete()
        
        # Delete the user
        user.delete()
        
        # Optionally, delete all tokens related to the user
        Token.objects.filter(user_id=user.id).delete()
        
        return Response({"detail": "Account successfully deleted."}, status=status.HTTP_204_NO_CONTENT)


class PatternAssignmentViewSet(viewsets.GenericViewSet, viewsets.mixins.CreateModelMixin):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
    http_method_names = ['post']

    def create(self, request, *args, **kwargs):
        user = self.request.user
        pattern_name = request.data.get('pattern_name')

        if not pattern_name:
            return Response({"detail": "Pattern name is required."}, status=status.HTTP_400_BAD_REQUEST)
        
        # Look up the pattern by name
        pattern = get_object_or_404(Pattern, name=pattern_name)

        # Get or create the user profile
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        # Assign the pattern to the user profile
        profile.pattern = pattern
        profile.save()

        return Response({"detail": "Pattern assigned successfully."}, status=status.HTTP_200_OK)
