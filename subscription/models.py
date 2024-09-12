from django.db import models
from django.contrib.auth.models import User


class Subscription(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    validity = models.IntegerField(help_text="Validity in days")
    price = models.IntegerField()
    start_limit = models.IntegerField()
    enroll_limit = models.IntegerField()
    level = models.IntegerField(default=0) 

    def __str__(self):
        return self.name


class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('Current', 'Current'),
        ('Upcoming', 'Upcoming'),
        ('Expired', 'Expired'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    subscription_start_date = models.DateTimeField()
    subscription_end_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Upcoming')
    renewed = models.BooleanField(default=False)
    enrolled_courses = models.IntegerField(default=0)
    started_courses = models.IntegerField(default=0)
    enrolled_classes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    payment = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.subscription.name}"
        
