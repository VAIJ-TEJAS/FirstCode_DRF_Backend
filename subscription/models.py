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
    payment_id = models.CharField(max_length=255, null=True, blank=True)
    order_id = models.CharField(max_length=255, null=True, blank=True)
    signature = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=50, null=True, blank=True)
    payment_method = models.CharField(max_length=100, null=True, blank=True)
    subscription_start_date = models.DateTimeField()
    subscription_end_date = models.DateTimeField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='Upcoming')
    renewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subscription.name} - {self.payment_id}"
        
