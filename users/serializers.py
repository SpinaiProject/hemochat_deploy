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
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=False, allow_null=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True)

    def validate_email(self, value):
        user_query = User.objects.filter(email=value)
        if user_query.exists():
            user = user_query.first()
            if user.signup_id:
                raise serializers.ValidationError("이 이메일은 이미 소셜 로그인으로 가입되었습니다.")
            else:
                raise serializers.ValidationError("이 이메일은 이미 사용 중입니다.")
        return value

    def validate_password1(self, password):
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
        return password

    def save(self, request):
        user = super().save(request)
        user.age = self.validated_data.get('age', None)
        user.gender = self.validated_data.get('gender', None)
        user.birthday = self.validated_data.get('birthday', None)
        user.phone_number = self.validated_data.get('phone_number', None)
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
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [ 'profile_image','username','phone_number','email', 'age',  'birthday','gender']

    def get_profile_image(self, obj):
        request = self.context.get('request')
        if obj.profile_image and hasattr(obj.profile_image, 'url'):
            return request.build_absolute_uri(obj.profile_image.url)
        return None
class IDCheckSerializer(serializers.Serializer):
    is_unique = serializers.BooleanField()


def validate_image(image):
    valid_extensions = ['jpg', 'jpeg', 'png']
    extension = image.name.split('.')[-1].lower()
    if extension not in valid_extensions:
        raise ValidationError("올바른 확장자가 아닙니다. jpg, jpeg, png 파일만 허용됩니다.")

    if image.size > 5 * 1024 * 1024:
        raise ValidationError("파일 크기는 5MB를 넘을 수 없습니다.")


class UserUpdateSerializer(serializers.ModelSerializer):
    profile_image = serializers.ImageField(validators=[validate_image])

    class Meta:
        model = User
        fields = ['profile_image']