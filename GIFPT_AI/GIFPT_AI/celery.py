import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'GIFPT_AI.settings')

app = Celery('GIFPT_AI')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
