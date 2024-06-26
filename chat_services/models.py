from django.db import models
from django.core.exceptions import ValidationError
from health_records.models import HealthRecordImage
from hemochat_project import settings
from django.db.models.signals import post_delete
from django.dispatch import receiver


class AssistantConfig(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    api_key = models.CharField(max_length=255)


class ChatRoom(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chatrooms', null=True, blank=True)
    health_records = models.ManyToManyField(HealthRecordImage, related_name='chatrooms')
    title = models.CharField(max_length=255, blank=False, default="AI 분석되지 않은 이미지입니다")
    chatroom_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_temporary = models.BooleanField(default=False)
    chat_num = models.IntegerField(default=0)


class TempChatroom(models.Model):
    chatroom_id = models.CharField(max_length=255, unique=True)
    chat_num = models.IntegerField(default=0)
    image = models.ImageField(upload_to='temp_images/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.chat_num > 5:
            raise ValidationError('chat_num cannot exceed 5')
        super().save(*args, **kwargs)


@receiver(post_delete, sender=TempChatroom)
def delete_associated_image(sender, instance, **kwargs):
    if instance.image:
        instance.image.delete(save=False)

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
