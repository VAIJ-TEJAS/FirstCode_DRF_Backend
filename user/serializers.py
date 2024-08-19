from rest_framework import serializers
from subscription.serializers import UserSubscriptionSerializer
from .models import Pattern, UserProfile
from django.contrib.auth.models import User


class PatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pattern
        fields = "__all__"


class UserProfileSerializer(serializers.ModelSerializer):
    pattern = PatternSerializer()
    current_subscription = UserSubscriptionSerializer()
    class Meta:
        model = UserProfile
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    subscriptions = UserSubscriptionSerializer(many=True, read_only=True)
    userprofile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = "__all__"
        extra_kwargs = {"password": {"write_only": True, "required": True}}
