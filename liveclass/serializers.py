from rest_framework import serializers
from .models import LiveClass, UserLiveClass

class BaseLiveClassSerializer(serializers.ModelSerializer):
    can_enroll = serializers.SerializerMethodField()
    has_enroll_limit_exceeded = serializers.SerializerMethodField()
    has_already_enrolled = serializers.SerializerMethodField()
    button_text = serializers.SerializerMethodField()
    user_live_class = serializers.SerializerMethodField()
    class_link = serializers.SerializerMethodField()

    class Meta:
        abstract = True

    def get_user_subscription(self):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return request.user.subscriptions.filter(status='Current').first()
        return None

    def get_can_enroll(self, obj):
        user_subscription = self.get_user_subscription()
        if obj.is_paid:
            if user_subscription and user_subscription.subscription.level > 0:
                return True
            return False
        return True

    def get_has_enroll_limit_exceeded(self, obj):
        user_subscription = self.get_user_subscription()
        if user_subscription:
            if user_subscription.enrolled_classes >= user_subscription.subscription.enroll_limit:
                return True
        return False

    def get_has_already_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Check if the user has already enrolled in the class
            return UserLiveClass.objects.filter(user=request.user, live_class=obj).exists()
        return False

    def get_button_text(self, obj):
        if self.get_has_enroll_limit_exceeded(obj):
            return "Enroll Limit Exceeded"
        if self.get_has_already_enrolled(obj):
            return "Join"
        if self.get_can_enroll(obj):
            return "Enroll"
        return "Upgrade Subscription"

    def get_user_live_class(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Fetch the UserLiveClass object for the current user and live class
            user_enrollment = UserLiveClass.objects.filter(user=request.user, live_class=obj).first()
            if user_enrollment:
                # Use the UserLiveClassSerializer to serialize the object
                return UserLiveClassSerializer(user_enrollment).data
        return None
    
    def get_class_link(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Check if the user has already enrolled
            user_enrollment = UserLiveClass.objects.filter(user=request.user, live_class=obj).first()
            if user_enrollment and user_enrollment.status == 'Approved':
                return obj.class_link
            return None
        return None

class LiveClassSerializer(BaseLiveClassSerializer):
    class Meta(BaseLiveClassSerializer.Meta):
        model = LiveClass
        fields = [
            'id', 'name', 'batch_name', 'start_date', 'duration',
            'daily_start_time', 'daily_end_time', 'cover_image',
            'short_description', 'medium', 'is_paid', 'class_link',
            'can_enroll', 'has_enroll_limit_exceeded', 'has_already_enrolled', 'button_text', 'user_live_class'
        ]


class MyLiveClassSerializer(BaseLiveClassSerializer):
    class Meta(BaseLiveClassSerializer.Meta):
        model = LiveClass
        fields = [
            'id', 'name', 'batch_name', 'start_date', 'duration',
            'daily_start_time', 'daily_end_time', 'cover_image',
            'short_description', 'medium', 'is_paid', 'class_link',
            'can_enroll', 'has_enroll_limit_exceeded', 'has_already_enrolled', 'button_text', 'user_live_class'
        ]

class DetailedLiveClassSerializer(BaseLiveClassSerializer):
    class Meta(BaseLiveClassSerializer.Meta):
        model = LiveClass
        fields = '__all__'

class UserLiveClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLiveClass
        fields = '__all__'

    def get_class_link(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            user_enrollment = UserLiveClass.objects.filter(user=request.user, live_class=obj).first()
            if user_enrollment and user_enrollment.status == 'Enrolled':
                return None
            return obj.class_link
        return None