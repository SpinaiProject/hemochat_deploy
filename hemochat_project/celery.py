import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hemochat_project.settings')

app = Celery('hemochat_project')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.conf.beat_schedule = {
    'save-chat-history-every-5-minutes': {
        'task': 'chat_services.tasks.save_chat_history_periodically',
        'schedule': crontab(minute='*/5'),
    },
}


app.autodiscover_tasks()
