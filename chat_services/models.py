import json
import uuid

from django.core.serializers.json import DjangoJSONEncoder
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


# 아래는 Assistant API Streaming이 지원되지 않을 때 사용할 모델들
class ChatRoom(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    health_records = models.ManyToManyField('health_records.HealthRecordImage', related_name='chatrooms', blank=True)
    chat_history = models.JSONField(blank=True, default=list)
    summarized_chat_history = models.JSONField(blank=True, default=list)
    last_entered = models.DateTimeField(auto_now=True)
    entered = models.BooleanField(default=False)
    leaved = models.BooleanField(default=True)
    def __str__(self):
        return f"ChatRoom {self.id}"
