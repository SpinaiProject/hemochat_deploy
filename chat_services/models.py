import uuid

from django.db import models
from django.db.models import Manager
from health_records.models import HealthRecordImage
from hemochat_project import settings


class AssistantConfig(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)


class ChatRoom(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chatrooms')
    health_records = models.ManyToManyField(HealthRecordImage, related_name='chatrooms')
    title = models.CharField(max_length=255, blank=True)
    chatroom_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)



# 아래는 Assistant API Streaming이 지원되지 않을 때 사용할 모델들
# class ChatRoom(models.Model):
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     title = models.CharField(max_length=50)
#     user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,related_name='chatrooms')
#     health_records = models.ManyToManyField('health_records.HealthRecordImage', related_name='chatrooms', blank=True)
#     chat_history = models.JSONField(blank=True, default=list)
#     summarized_chat_history = models.JSONField(blank=True, default=list)
#     last_entered = models.DateTimeField(auto_now=True)
#     entered = models.BooleanField(default=False)
#     leaved = models.BooleanField(default=True)
#     def __str__(self):
#         return f"ChatRoom {self.id}"
