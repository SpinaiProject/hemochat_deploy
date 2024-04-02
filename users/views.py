import os,json
from json import JSONDecodeError
import requests

from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.kakao import views as kakao_view
from allauth.socialaccount.providers.google import views as google_view
from dj_rest_auth.registration.views import SocialLoginView

from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response

from .serializers import *

BASE_URL = settings.BASE_URL
KAKAO_FRONT_REDIRECT = os.environ.get('FRONT_KAKAO_REDIRECT')
GOOGLE_CALLBACK_URI = os.environ.get('FRONT_GOOGLE_REDIRECT')


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = DetailSerializer


# def kakao_login(request):
#     client_id = os.environ.get("KAKAO_REST_API_KEY")
#     print("1. api key: ", client_id)
#     return redirect(
#         f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={KAKAO_FRONT_REDIRECT}&response_type=code&scope=account_email")


def kakao_login(request):
    client_id = os.environ.get('KAKAO_REST_API_KEY')
    code = request.GET.get('code')

    # code로 access token 요청
    token_request = requests.post(
        f"https://kauth.kakao.com/oauth/token?grant_type=authorization_code&client_id={client_id}&redirect_uri={KAKAO_FRONT_REDIRECT}&code={code}",
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )

    try:
        token_response_json = token_request.json()
    except ValueError:
        return JsonResponse({'error': 'Invalid response format'}, status=400)

    error = token_response_json.get("error", None)
    if error is not None:
        return JsonResponse({'error': error}, status=400)

    access = token_response_json.get("access_token")
    profile_request = requests.post(
        "https://kapi.kakao.com/v2/user/me",
        headers={
            "Authorization": f"Bearer {access}",
            "Content-type": "application/x-www-form-urlencoded;charset=utf-8}"}
    )
    profile_json = profile_request.json()
    # print("profile_json by profile request: ", profile_json)
    signup_id = profile_json.get("id")
    email = profile_json.get("kakao_account").get("email", None)

    try:
        user = User.objects.get(email=email)
        if user.signup_id:
            created = False
        else:
            return JsonResponse({'error': '이 이메일은 이미 사용 중입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        user = User.objects.create_user(signup_id=signup_id, email=email)
        created = True

    token = TokenObtainPairSerializer.get_token(user)
    print("final token:",token)
    access = str(token.access_token)
    refresh = str(token)

    return JsonResponse({
        "created": created,
        "access": access,
        "refresh": refresh
    })

# class KakaoLogin(SocialLoginView):
#     adapter_class = kakao_view.KakaoOAuth2Adapter
#     callback_url = KAKAO_FRONT_REDIRECT
#     client_class = OAuth2Client


@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def kakao_logout(request):
    access = request.GET.get('access')  # 액세스 토큰을 쿼리 파라미터로 넘겨 받아 로그아웃 하는 방식
    if not access:
        return JsonResponse({'error': 'Access token is required'}, status=400)

    headers = {"Authorization": f"Bearer {access}"}
    logout_response = requests.post("https://kapi.kakao.com/v1/user/logout", headers=headers)

    if logout_response.status_code == 200:
        return JsonResponse({'message': '성공적으로 로그아웃 했습니다'})  # 200을 받으면, 프론트에서 저장하고있던 jwt토큰을 만료시키고
        # 홈페이지로 리다이렉트 시켜야함
    else:
        return JsonResponse({'error': '로그아웃 실패'}, status=logout_response.status_code)


# def google_login(request):
#     scope = "https://www.googleapis.com/auth/userinfo.email"
#     client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
#     return redirect(
#         f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={GOOGLE_CALLBACK_URI}&response_type=code&scope={scope}")


def google_login(request):
    client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("SOCIAL_AUTH_GOOGLE_SECRET")
    state = os.environ.get("STATE")
    try:
        data = json.loads(request.body)
        code = data.get('code')
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다. JSON 형식이 올바른지 확인해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)
    token_req = requests.post(
        f"https://oauth2.googleapis.com/token?client_id={client_id}&client_secret={client_secret}&code={code}&grant_type=authorization_code&redirect_uri={GOOGLE_CALLBACK_URI}&state={state}")

    token_req_json = token_req.json()
    error = token_req_json.get("error")
    if error is not None:
        raise ImproperlyConfigured(error)
    access = token_req_json.get('access_token')

    profile_req = requests.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access}")
    profile_req_status = profile_req.status_code
    if profile_req_status != 200:
        return JsonResponse({'error': '회원정보 조회 실패'}, status=status.HTTP_400_BAD_REQUEST)

    profile_req_json = profile_req.json()
    user_id = profile_req_json.get('user_id')
    email = profile_req_json.get('email')

    try:
        user = User.objects.get(email=email)
        if user.signup_id:
            created = False
        else:
            return JsonResponse({'error': '이 이메일은 이미 사용 중입니다.'}, status=status.HTTP_400_BAD_REQUEST)
    except User.DoesNotExist:
        user = User.objects.create_user(signup_id=user_id, email=email)
        created = True

    token = TokenObtainPairSerializer.get_token(user)
    access = str(token.access_token)
    refresh = str(token)

    return JsonResponse({
        "created": created,
        "access": access,
        "refresh": refresh
    })


class GoogleLogin(SocialLoginView):
    adapter_class = google_view.GoogleOAuth2Adapter
    callback_url = GOOGLE_CALLBACK_URI
    client_class = OAuth2Client


class EmailSignupView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = CustomSignupSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save(request)
            if user:
                return Response({"detail": "성공적으로 회원가입 되었습니다"}, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# class EmailAlreadyExistAPIView(APIView):
#     permission_classes = [AllowAny]
#
#     def post(self, request, *args, **kwargs):
#         email = request.data.get('email', None)
#
#         if email is None:
#             return Response({"error": "이메일을 입력하세요"}, status=status.HTTP_400_BAD_REQUEST)
#
#         user_exists = User.objects.filter(
#             username=email
#         ).exists() or User.objects.filter(
#             kakao_email=email
#         ).exists() or User.objects.filter(
#             google_email=email
#         ).exists()
#
#         if user_exists:
#             return Response({"exists": True}, status=status.HTTP_200_OK)
#         else:
#             return Response({"exists": False}, status=status.HTTP_200_OK)


# class CustomTokenObtainPairView(TokenObtainPairView):
#     serializer_class = CustomTokenObtainPairSerializer


# 마이페이지
class MyPageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = DetailSerializer(user)
        return Response(serializer.data)


# 개인정보 업데이트 및 삭제
class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, format=None):
        request.user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# 전화번호 인증 관련 뷰함수(인증번호 발송, 검증)
class SendVerificationCodeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        if phone_number is None:
            return Response({'error': '전화번호를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        user.send_verification_code()
        return Response({'message': '인증 코드가 발송되었습니다.'}, status=status.HTTP_200_OK)


class VerifyPhoneNumberAPIView(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        if phone_number is None or code is None:
            return Response({'error': '전화번호와 인증 코드를 모두 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        if user.verify_phone_number(code):
            return Response({'message': '전화번호가 인증되었습니다.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': '유효하지 않은 인증 코드입니다.'}, status=status.HTTP_400_BAD_REQUEST)


# 이메일 찾기 기능
class SendEmailVerificationCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        if phone_number is None:
            return Response({'error': '전화번호가 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        user.send_verification_code()
        return Response({'message': '인증 코드가 발송되었습니다.'}, status=status.HTTP_200_OK)


class VerifyPhoneNumberAndReturnEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        verification_code = request.data.get('code')
        if phone_number is None or verification_code is None:
            return Response({'error': '전화번호와 인증 코드가 모두 필요합니다.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        if user.verify_phone_number(verification_code):
            return Response({'email': user.email}, status=status.HTTP_200_OK)
        else:
            return Response({'error': '유효하지 않은 인증 코드입니다.'}, status=status.HTTP_400_BAD_REQUEST)


# 비밀번호 찾기 기능
class RequestPhoneNumberForPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')

        if not email:
            return Response({'error': '이메일을 입력해주세요'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email=email, signup_id__isnull=True).first()
        if user is not None:
            return Response(status=status.HTTP_200_OK)
        else:
            return Response({'error': "사용자를 찾을 수 없습니다. 이메일을 확인하고 다시 시도하십시오."}, status=status.HTTP_404_NOT_FOUND)


class VerifyPhoneNumberForPassword(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        input_phone_number = request.data.get('phone_number')

        if not email or not input_phone_number:
            return Response({'error': '이메일과 전화번호는 필수 항목입니다.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, username=email)
        if user.phone_number == input_phone_number:
            user.send_verification_code()
            return Response({'message': '인증 코드가 발송되었습니다. 전화를 확인해 주세요.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': '전화번호가 일치하지 않습니다.'}, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        verification_code = request.data.get('verification_code')
        new_password = request.data.get('new_password')

        user = get_object_or_404(User, username=email)

        if user.verify_phone_number(verification_code):
            user.set_password(new_password)
            user.save()
            return Response({'message': '비밀번호가 성공적으로 변경되었습니다.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': '인증번호가 틀립니다.'}, status=status.HTTP_400_BAD_REQUEST)
