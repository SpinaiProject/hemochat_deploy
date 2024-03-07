import re
from .models import User
from rest_framework import serializers
from dj_rest_auth.registration.serializers import RegisterSerializer


# class SignupSerializer(RegisterSerializer):
#     def custom_signup(self, request, user):
#         return super().custom_signup(request, user)


class CustomSignupSerializer(RegisterSerializer):
    nickname = serializers.CharField(max_length=100, required=False)
    kakao_email = serializers.EmailField(required=False, allow_null=True)
    google_email = serializers.EmailField(required=False, allow_null=True)
    random_directory_name = serializers.CharField(max_length=20, required=False)
    age = serializers.IntegerField(required=False, allow_null=True)
    gender = serializers.ChoiceField(choices=User.GENDER_CHOICES, required=False, allow_null=True)
    birthday = serializers.DateField(required=False, allow_null=True)
    birth_year = serializers.IntegerField(required=False, allow_null=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True)

    def validate_kakao_email(self, value):
        if value and User.objects.filter(kakao_email=value).exists():
            raise serializers.ValidationError("This kakao_email is already in use.")
        return value

    def validate_google_email(self, value):
        if value and User.objects.filter(google_email=value).exists():
            raise serializers.ValidationError("This google_email is already in use.")
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
        user.nickname = self.validated_data.get('nickname')
        user.kakao_email = self.validated_data.get('kakao_email', None)
        user.google_email = self.validated_data.get('google_email', None)
        user.random_directory_name = self.validated_data.get('random_directory_name', None)
        user.age = self.validated_data.get('age', None)
        user.gender = self.validated_data.get('gender', None)
        user.birthday = self.validated_data.get('birthday', None)
        user.birth_year = self.validated_data.get('birth_year', None)
        user.phone_number = self.validated_data.get('phone_number', None)
        user.save()
        return user


class DetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['username', 'nickname', 'kakao_email', 'google_email', 'random_directory_name', 'age', 'gender',
                  'birthday', 'birth_year', 'phone_number']


class IDCheckSerializer(serializers.Serializer):
    is_unique = serializers.BooleanField()
