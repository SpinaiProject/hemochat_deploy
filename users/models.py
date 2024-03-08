import uuid
import random

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.crypto import get_random_string
from .utils import send_sms


def generate_default_email():
    return str(uuid.uuid4()) + '@example.com'


class User(AbstractUser):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    nickname = models.CharField(max_length=100, null=True, blank=True)
    kakao_email = models.EmailField(null=True, blank=True)
    google_email = models.EmailField(null=True, blank=True)
    random_directory_name = models.CharField(max_length=20, unique=True, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    birth_year = models.PositiveIntegerField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, unique=True, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.random_directory_name:
            self.random_directory_name = get_random_string(20)
        super().save(*args, **kwargs)

    def send_verification_code(self):
        self.verification_code = '{:06d}'.format(random.randint(0, 999999))
        self.save()
        send_sms(self.phone_number, f'[헤모챗] 인증번호는 {self.verification_code}입니다.')
        success, response = send_sms(self.phone_number, f'[헤모챗] 인증번호는 {self.verification_code}입니다.')
        if success:
            print("SMS sent successfully:", response)
        else:
            print("Fail to send SMS:", response)

    def verify_phone_number(self, code):
        if self.verification_code == code:
            self.phone_verified = True
            self.verification_code = None
            self.save()
            return True
        return False
