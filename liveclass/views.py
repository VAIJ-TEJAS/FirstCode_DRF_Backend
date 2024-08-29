from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import LiveClass, UserLiveClass
from .serializers import (
    DetailedLiveClassSerializer,
    LiveClassSerializer,
    UserLiveClassSerializer,
    MyLiveClassSerializer,
)


class LiveClassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LiveClass.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DetailedLiveClassSerializer
        return LiveClassSerializer


class MyLiveClassViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = LiveClass.objects.all()

    def get_serializer_class(self):
        if self.action == "retrieve":
            return DetailedLiveClassSerializer
        return MyLiveClassSerializer

    def get_queryset(self):
        return LiveClass.objects.filter(userliveclass__user=self.request.user)


class UserLiveClassViewSet(viewsets.ModelViewSet):
    queryset = UserLiveClass.objects.all()
    serializer_class = UserLiveClassSerializer

    def create(self, request, *args, **kwargs):
        live_class_id = request.data.get('live_class')
        try:
            live_class = LiveClass.objects.get(id=live_class_id)
        except LiveClass.DoesNotExist:
            return Response({'detail': 'Live class not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Use the serializer methods to check enrollment criteria
        serializer = LiveClassSerializer(live_class, context={'request': request})

        can_enroll = serializer.get_can_enroll(live_class)
        has_already_enrolled = serializer.get_has_already_enrolled(live_class)
        has_enroll_limit_exceeded = serializer.get_has_enroll_limit_exceeded(live_class)

        if has_enroll_limit_exceeded:
            return Response({'detail': 'Enrollment limit exceeded.'}, status=status.HTTP_400_BAD_REQUEST)

        if not can_enroll:
            return Response({'detail': 'User cannot enroll in this class.'}, status=status.HTTP_403_FORBIDDEN)

        if has_already_enrolled:
            return Response({'detail': 'User has already enrolled in this class.'}, status=status.HTTP_400_BAD_REQUEST)

        # Create UserLiveClass instance
        user_live_class = UserLiveClass.objects.create(
            user=request.user,
            live_class=live_class
        )
        
        # Increment enrolled_classes for the user's subscription
        user_subscription = request.user.subscriptions.filter(status='Current').first()
        if user_subscription:
            user_subscription.enrolled_classes += 1
            user_subscription.save()

        serializer = self.get_serializer(user_live_class)
        return Response(serializer.data, status=status.HTTP_201_CREATED)