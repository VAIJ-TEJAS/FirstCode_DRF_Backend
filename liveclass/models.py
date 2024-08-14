from django.db import models
from django.contrib.auth.models import User

class LiveClass(models.Model):
    name = models.CharField(max_length=255)
    batch_name = models.CharField(max_length=255)
    start_date = models.DateField()
    duration = models.IntegerField(help_text="Duration in days")
    daily_start_time = models.TimeField()
    daily_end_time = models.TimeField()
    cover_image = models.ImageField(upload_to='live_classes/', blank=True, null=True)
    short_description = models.CharField(max_length=500)
    long_description = models.TextField()
    requirements = models.TextField()
    medium = models.CharField(max_length=100)
    class_link = models.URLField()
    is_paid = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.batch_name}"


class UserLiveClass(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    live_class = models.ForeignKey(LiveClass, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.live_class.name}"