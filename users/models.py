import re
import uuid
import random

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.core.exceptions import ValidationError

from django.db import models
from django.utils.crypto import get_random_string
from .utils import send_sms


def generate_default_email():
    return str(uuid.uuid4()) + '@example.com'


class UserManager(BaseUserManager):
    def validate_password(self, password):
        if not password:
            raise ValidationError("비밀번호를 입력해야 합니다.")
        if len(password) < 8:
            raise ValidationError("비밀번호는 최소 8자 이상이어야 합니다.")
        if not re.findall(r'[A-Za-z]', password):
            raise ValidationError("비밀번호에는 최소 하나의 영문자가 포함되어야 합니다.")
        if not re.findall(r'[0-9]', password):
            raise ValidationError("비밀번호에는 최소 하나의 숫자가 포함되어야 합니다.")
        if not re.findall(r'[!@#$%^&*()-_=+]', password):
            raise ValidationError("비밀번호에는 최소 하나의 특수문자가 포함되어야 합니다.")
        if re.findall(r'[^a-zA-Z0-9!@#$%^&*()-_=+]', password):
            raise ValidationError("비밀번호에는 영문 대소문자, 숫자, 특수문자 외에 다른 문자를 포함할 수 없습니다.")

    def create_user(self, signup_id, password=None, **extra_fields):
        if not signup_id:
            signup_id = None
        if not extra_fields.get('random_directory_name'):
            extra_fields['random_directory_name'] = get_random_string(20)
        if not extra_fields.get('username'):
            extra_fields['username'] = get_random_string(10)

        user = self.model(signup_id=signup_id, **extra_fields)
        self.validate_password(password)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, signup_id, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(signup_id, password, **extra_fields)


class User(AbstractUser):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    email = models.EmailField(unique=True, blank=False, null=False)
    nickname = models.CharField(max_length=100, null=True, blank=True)
    username = models.CharField(max_length=150, unique=False, blank=True)
    signup_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    random_directory_name = models.CharField(max_length=20, unique=True, blank=True)

    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    phone_verified = models.BooleanField(default=False)
    verification_code = models.CharField(max_length=6, blank=True, null=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.random_directory_name:
            self.random_directory_name = get_random_string(20)
        if not self.username:
            self.username = get_random_string(10)
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
