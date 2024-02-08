from django.db import models
from django.db.models import Manager

from hemochat_project import settings


class AssistantConfig(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)
    model = models.CharField(max_length=255, default='gpt-3.5-turbo')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ChatThread(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='assistant_sessions')
    thread_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    objects: Manager = models.Manager()
    # title= models.CharField(max_length=255, blank=True)
