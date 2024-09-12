from django.db import models
from django.contrib.auth.models import User
from subscription.models import Subscription
from django.utils import timezone
from datetime import timedelta

class Order(models.Model):
    SUBSCRIPTION_TYPE_CHOICES = [
        ('NEW', 'New'),
        ('RENEW', 'Renew'),
    ]
    
    order_id = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    subscription_type = models.CharField(max_length=5, choices=SUBSCRIPTION_TYPE_CHOICES)
    completed = models.BooleanField(default=False) 
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.order_id} - {self.subscription_type}"
    
    @staticmethod
    def delete_expired_orders():
        expiration_time = timezone.now() - timedelta(minutes=12)
        expired_orders = Order.objects.filter(completed=False, created_at__lt=expiration_time)
        expired_orders.delete()  # Delete expired orders
