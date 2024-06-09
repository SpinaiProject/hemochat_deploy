from django.db import models
from django.utils.crypto import get_random_string
from users.models import User


def user_directory_path(instance, filename):
    ext = filename.split('.')[-1]
    random_filename = get_random_string(20) + '.' + ext
    if instance.user:
        directory = instance.user.random_directory_name
    else:
        directory = 'anon_' + get_random_string(10)
    return '{0}/{1}'.format(directory, random_filename)

# class HealthRecordFolder(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     created_at = models.DateTimeField(auto_now_add=True)


class HealthRecordImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(upload_to=user_directory_path)
    ocr_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
