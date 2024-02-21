from django.db import models
from django.utils.crypto import get_random_string
from users.models import User


def user_directory_path(instance, filename):
    ext = filename.split('.')[-1]
    random_filename = get_random_string(20) + '.' + ext
    return '{0}/{1}/{2}'.format(instance.folder.user.random_directory_name, instance.folder.id, random_filename)


class HealthRecordFolder(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class HealthRecordImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    folder = models.ForeignKey(HealthRecordFolder, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to=user_directory_path)
    ocr_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
