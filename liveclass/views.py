from rest_framework import viewsets
from .models import LiveClass, UserLiveClass
from .serializers import LiveClassSerializer, UserLiveClassSerializer

class LiveClassViewSet(viewsets.ModelViewSet):
    queryset = LiveClass.objects.all()
    serializer_class = LiveClassSerializer

class UserLiveClassViewSet(viewsets.ModelViewSet):
    queryset = UserLiveClass.objects.all()
    serializer_class = UserLiveClassSerializer
