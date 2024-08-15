from rest_framework import viewsets
from .models import Pattern, UserProfile
from .serializers import PatternSerializer, UserProfileSerializer

class PatternViewSet(viewsets.ModelViewSet):
    queryset = Pattern.objects.all()
    serializer_class = PatternSerializer

class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    serializer_class = UserProfileSerializer
