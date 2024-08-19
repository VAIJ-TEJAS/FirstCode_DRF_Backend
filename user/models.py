from django.db import models
from django.contrib.auth.models import User
from subscription.models import UserSubscription

class Pattern(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_name_change = models.DateTimeField(null=True, blank=True)
    pattern = models.ForeignKey(Pattern, on_delete=models.SET_NULL, null=True, blank=True)
    current_subscription = models.ForeignKey(UserSubscription, on_delete=models.SET_NULL, null=True, blank=True) 

    def __str__(self):
        return self.user.username