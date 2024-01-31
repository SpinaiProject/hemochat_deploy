from django.db import models
from django.utils.crypto import get_random_string
from users.models import User


def user_directory_path(instance, filename):
    ext = filename.split('.')[-1]
    random_filename = get_random_string(20) + '.' + ext
    return '{0}/{1}'.format(instance.user.random_directory_name, random_filename)


class HealthRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ImageField(upload_to=user_directory_path)
    ocr_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

