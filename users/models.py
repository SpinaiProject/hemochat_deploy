import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.crypto import get_random_string


def generate_default_email():
    return str(uuid.uuid4()) + '@example.com'


class User(AbstractUser):
    nickname = models.CharField(max_length=100)
    kakao_email = models.EmailField(unique=True, default=generate_default_email)
    random_directory_name = models.CharField(max_length=20, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.random_directory_name:
            self.random_directory_name = get_random_string(20)
        super().save(*args, **kwargs)