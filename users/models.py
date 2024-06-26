import re
import uuid
import random

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as BaseUserManager
from django.core.exceptions import ValidationError

from django.db import models
from django.utils.crypto import get_random_string
from .utils import send_sms
from django.utils import timezone

def generate_default_email():
    return str(uuid.uuid4()) + '@example.com'


class UserManager(BaseUserManager):

    def create_user(self, signup_id, password=None, **extra_fields):
        if not signup_id:
            signup_id = None
        if not extra_fields.get('random_directory_name'):
            extra_fields['random_directory_name'] = get_random_string(20)
        if not extra_fields.get('username'):
            extra_fields['username'] = get_random_string(10)

        user = self.model(signup_id=signup_id, **extra_fields)
        if password:
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
    username = models.CharField(max_length=150, unique=False, blank=True)
    signup_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    random_directory_name = models.CharField(max_length=20, unique=True, blank=True)

    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, null=True, blank=True)
    birthday = models.DateField(null=True, blank=True)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    first_name = None
    last_name = None

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        self.full_clean()
        if not self.random_directory_name:
            self.random_directory_name = get_random_string(20)
        if not self.username:
            self.username = get_random_string(10)
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.phone_number and (not self.phone_number.isdigit() or len(self.phone_number) != 11 or not self.phone_number.startswith('010')):
            raise ValidationError('Phone number must be an 11-digit number starting with 010.')




class VerificationCode(models.Model):
    phone_number = models.CharField(max_length=15)
    code = models.CharField(max_length=6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    phone_verified = models.BooleanField(default=False)

    def send_verification_code(self):
        self.code = '{:06d}'.format(random.randint(0, 999999))

        success, response = send_sms(self.phone_number, f'[헤모챗] 인증번호는 {self.code}입니다.')
        if success:
            self.save()
            return True
        else:
            return False

    def is_valid(self):
        return timezone.now() < self.created_at + timezone.timedelta(minutes=10)

    def verify_code(self, code):
        if self.code == code and self.is_valid():
            self.phone_verified = True
            self.save()
            return True
        return False