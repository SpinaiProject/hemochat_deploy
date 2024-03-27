import re
from .models import User
from rest_framework import serializers
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


# class SignupSerializer(RegisterSerializer):
#     def custom_signup(self, request, user):
#         return super().custom_signup(request, user)


class CustomSignupSerializer(RegisterSerializer):
    signup_id = serializers.CharField(max_length=255, required=True)
    nickname = serializers.CharField(max_length=100, required=False)
    random_directory_name = serializers.CharField(max_length=20, required=False)
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=False, allow_null=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    birth_year = serializers.IntegerField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True)

    def validate_email(self, value):
        if value and User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

    def validate_password1(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("The password must be at least 8 characters long.")

        if not re.findall('[a-z]', value):
            raise serializers.ValidationError("The password must contain at least one lowercase letter.")
        if not re.findall('[0-9]', value):
            raise serializers.ValidationError("The password must contain at least one digit.")
        if not re.findall('[^a-zA-Z0-9]', value):
            raise serializers.ValidationError("The password must contain at least one special character.")

        return value

    def save(self, request):
        user = super().save(request)
        user.nickname = self.validated_data.get('nickname', None)
        user.random_directory_name = self.validated_data.get('random_directory_name', None)
        user.age = self.validated_data.get('age', None)
        user.gender = self.validated_data.get('gender', None)
        user.birthday = self.validated_data.get('birthday', None)
        user.birth_year = self.validated_data.get('birth_year', None)
        user.phone_number = self.validated_data.get('phone_number', None)
        user.signup_id = self.validated_data.get('signup_id')
        user.save()
        return user


# class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
#     username_field = User.EMAIL_FIELD
#
#     def validate(self, attrs):
#         email_validator = EmailValidator()
#         email = attrs.get('email', '')
#
#         try:
#             email_validator(email)
#         except ValidationError:
#             raise ValidationError('Invalid email format.')
#         attrs['username'] = attrs['email']
#         return super().validate(attrs)
#
#     @classmethod
#     def get_token(cls, user):
#         token = super().get_token(user)
#         token['email'] = user.email
#         return token

class DetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['signup_id', 'username', 'nickname', 'random_directory_name', 'age', 'gender',
                  'birthday', 'birth_year', 'phone_number']


class IDCheckSerializer(serializers.Serializer):
    is_unique = serializers.BooleanField()


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['password', 'nickname', 'phone_number']
        extra_kwargs = {
            'password': {'write_only': True},
            'phone_number': {'validators': []},
        }

    def validate_username(self, value):
        if User.objects.filter(username=value).exclude(pk=self.instance.pk).exists():
            raise serializers.ValidationError("이미 사용중인 이메일입니다")
        return value

    def validate_phone_number(self, value):
        if not value.isdigit() or not len(value) == 11 or not value.startswith('010'):
            raise serializers.ValidationError("휴대폰 번호는 '010'으로 시작하는 11자리의 숫자여야 합니다.")
        return value
