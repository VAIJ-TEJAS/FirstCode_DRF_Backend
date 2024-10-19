import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FirstCode_DRF_Backend.settings')

app = Celery('FirstCode_DRF_Backend')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Optional: configure your message broker (e.g., Redis)
app.conf.broker_url = 'redis://localhost:6379/0'  # Change to your broker configuration

