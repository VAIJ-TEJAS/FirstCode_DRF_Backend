from django.db import models

class Subscription(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    validity = models.IntegerField(help_text="Validity in days")
    price = models.IntegerField()
    start_limit = models.DateTimeField()
    enroll_limit = models.IntegerField()

    def __str__(self):
        return self.name

class UserSubscription(models.Model):
    subscription = models.ForeignKey(Subscription, on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=255)
    order_id = models.CharField(max_length=255)
    signature = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50)
    payment_method = models.CharField(max_length=100)
    subscription_start_date = models.DateTimeField()
    subscription_end_date = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subscription.name} - {self.payment_id}"