from rest_framework import serializers
from .models import LiveClass, UserLiveClass

class LiveClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveClass
        fields = '__all__'

class UserLiveClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLiveClass
        fields = '__all__'
