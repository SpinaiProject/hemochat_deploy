from abc import ABC

from .models import User
from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer


class SignupSerializer(RegisterSerializer):
    def custom_signup(self, request, user):
        return super().custom_signup(request, user)


class DetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('nickname', 'kakao_email')


class IDCheckSerializer(serializers.Serializer):
    is_unique = serializers.BooleanField()
