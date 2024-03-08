import os
from json import JSONDecodeError
import requests

from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.kakao import views as kakao_view
from allauth.socialaccount.providers.google import views as google_view
from allauth.socialaccount.models import SocialAccount
from dj_rest_auth.registration.views import SocialLoginView

from django.http import JsonResponse
from django.shortcuts import redirect, get_object_or_404
from django.conf import settings
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response

from .serializers import *

BASE_URL = settings.BASE_URL
KAKAO_CALLBACK_URI = settings.BASE_URL + 'api/users/kakao/callback/'
KAKAO_FINISH_URI = settings.BASE_URL + 'api/users/kakao/login/finish/'
GOOGLE_CALLBACK_URI = settings.BASE_URL + 'api/users/google/callback/'


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = DetailSerializer


# api_key => code => access_token => profile
def kakao_login(request):
    client_id = os.environ.get("KAKAO_REST_API_KEY")
    print("1. api key: ", client_id)
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code&scope=account_email")


def kakao_callback(request):
    client_id = os.environ.get('KAKAO_REST_API_KEY')
    code = request.GET.get('code')

    # code로 access token 요청
    token_request = requests.post(
        f"https://kauth.kakao.com/oauth/token?grant_type=authorization_code&client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&code={code}",
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )

    try:
        token_response_json = token_request.json()
    except ValueError:
        return JsonResponse({'error': 'Invalid response format'}, status=400)

    error = token_response_json.get("error", None)
    if error is not None:
        return JsonResponse({'error': error}, status=400)

    access_token = token_response_json.get("access_token")
    profile_request = requests.post(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    profile_json = profile_request.json()
    kakao_account = profile_json.get("kakao_account")
    email = kakao_account.get("email", None)

    # 사용자 존재 여부와 관계없이 수행될 로직
    data = {'access_token': access_token, 'code': code}
    accept = requests.post(KAKAO_FINISH_URI, data=data)
    accept_status = accept.status_code

    if accept_status != 200:
        return JsonResponse({'err_msg': 'failed to process'}, status=accept_status)

    accept_json = accept.json()
    return JsonResponse(accept_json)


class KakaoLogin(SocialLoginView):
    adapter_class = kakao_view.KakaoOAuth2Adapter
    callback_url = KAKAO_CALLBACK_URI
    client_class = OAuth2Client


@permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
def kakao_logout(request):
    access_token = request.GET.get('access_token')  # 액세스 토큰을 쿼리 파라미터로 넘겨 받아 로그아웃 하는 방식
    if not access_token:
        return JsonResponse({'error': 'Access token is required'}, status=400)

    headers = {"Authorization": f"Bearer {access_token}"}
    logout_response = requests.post("https://kapi.kakao.com/v1/user/logout", headers=headers)

    if logout_response.status_code == 200:
        return JsonResponse({'message': 'Logout successful'})  # 200을 받으면, 프론트에서 저장하고있던 jwt토큰을 만료시키고
        # 홈페이지로 리다이렉트 시켜야함
    else:
        return JsonResponse({'error': 'Logout failed'}, status=logout_response.status_code)


def google_login(request):
    scope = "https://www.googleapis.com/auth/userinfo.email"
    client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
    return redirect(
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&response_type=code&redirect_uri={GOOGLE_CALLBACK_URI}&scope={scope}")


def google_callback(request):
    client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("SOCIAL_AUTH_GOOGLE_SECRET")
    state = os.environ.get("STATE")
    code = request.GET.get('code')
    # 1. 받은 코드로 구글에 access token 요청
    token_req = requests.post(
        f"https://oauth2.googleapis.com/token?client_id={client_id}&client_secret={client_secret}&code={code}&grant_type=authorization_code&redirect_uri={GOOGLE_CALLBACK_URI}&state={state}")

    ### 1-1. json으로 변환 & 에러 부분 파싱
    token_req_json = token_req.json()
    error = token_req_json.get("error")

    ### 1-2. 에러 발생 시 종료
    if error is not None:
        raise JSONDecodeError(error)

    ### 1-3. 성공 시 access_token 가져오기
    access_token = token_req_json.get('access_token')

    # 2. 가져온 access_token으로 이메일값을 구글에 요청
    email_req = requests.get(f"https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={access_token}")
    email_req_status = email_req.status_code

    ### 2-1. 에러 발생 시 400 에러 반환
    if email_req_status != 200:
        return JsonResponse({'err_msg': 'failed to get email'}, status=status.HTTP_400_BAD_REQUEST)

    ### 2-2. 성공 시 이메일 가져오기
    email_req_json = email_req.json()
    email = email_req_json.get('email')

    # 3. 전달받은 이메일, access_token, code를 바탕으로 회원가입/로그인
    try:
        # 전달받은 이메일로 등록된 유저가 있는지 탐색
        user = User.objects.get(email=email)

        # FK로 연결되어 있는 socialaccount 테이블에서 해당 이메일의 유저가 있는지 확인
        social_user = SocialAccount.objects.get(user=user)

        # 있는데 구글계정이 아니어도 에러
        # if social_user.provider != 'google':
        #     return JsonResponse({'err_msg': 'no matching social type'}, status=status.HTTP_400_BAD_REQUEST)

        # 이미 Google로 제대로 가입된 유저 => 로그인 & 해당 우저의 jwt 발급
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(f"{BASE_URL}api/users/google/login/finish/", data=data)
        accept_status = accept.status_code

        # 뭔가 중간에 문제가 생기면 에러
        if accept_status != 200:
            return JsonResponse({'err_msg': 'failed to signin'}, status=accept_status)

        accept_json = accept.json()
        print("jwt request response : ", accept_json)
        accept_json.pop('user', None)
        return JsonResponse(accept_json)

    except User.DoesNotExist:
        # 전달받은 이메일로 기존에 가입된 유저가 아예 없으면 => 새로 회원가입 & 해당 유저의 jwt 발급
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(f"{BASE_URL}api/users/google/login/finish/", data=data)
        accept_status = accept.status_code
        print("jwt request response: ", accept)
        # 뭔가 중간에 문제가 생기면 에러
        if accept_status != 200:
            return JsonResponse({'err_msg': 'failed to signup'}, status=accept_status)

        accept_json = accept.json()
        print("json formatted:", accept_json)
        accept_json.pop('user', None)
        return JsonResponse(accept_json)

    except SocialAccount.DoesNotExist:
        # User는 있는데 SocialAccount가 없을 때 (=일반회원으로 가입된 이메일일때)
        return JsonResponse({'err_msg': 'email exists but not social user'}, status=status.HTTP_400_BAD_REQUEST)


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
                return Response({"detail": "signed up successfully."}, status=status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class EmailAlreadyExistAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', None)

        if email is None:
            return Response({"error": "email field not provided"}, status=status.HTTP_400_BAD_REQUEST)

        user_exists = User.objects.filter(
            username=email
        ).exists() or User.objects.filter(
            kakao_email=email
        ).exists() or User.objects.filter(
            google_email=email
        ).exists()

        if user_exists:
            return Response({"exists": True}, status=status.HTTP_200_OK)
        else:
            return Response({"exists": False}, status=status.HTTP_200_OK)


# 개인정보 업데이트
class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 전화번호 인증 관련 뷰함수(인증번호 발송, 검증)
class SendVerificationCodeAPIView(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        if phone_number is None:
            return Response({'error': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        user.send_verification_code()
        return Response({'message': 'Verification code sent.'}, status=status.HTTP_200_OK)


class VerifyPhoneNumberAPIView(APIView):
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        code = request.data.get('code')
        if phone_number is None or code is None:
            return Response({'error': 'Phone number and code are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        if user.verify_phone_number(code):
            return Response({'message': 'Phone number verified.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)


# 이메일 찾기 기능
class SendEmailVerificationCodeAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        if phone_number is None:
            return Response({'error': 'Phone number is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        user.send_verification_code()
        return Response({'message': 'Verification code sent.'}, status=status.HTTP_200_OK)


class VerifyPhoneNumberAndReturnEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        verification_code = request.data.get('code')
        if phone_number is None or verification_code is None:
            return Response({'error': 'Phone number and verification code are required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        if user.verify_phone_number(verification_code):
            return Response({'email': user.email}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)


# 비밀번호 찾기 기능
class RequestPhoneNumberView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        if not email:
            return Response({'error': 'Email is required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, username=email)
        return Response({"message": "Please enter the phone number associated with this account to proceed."},
                        status=status.HTTP_200_OK)


class VerifyPhoneNumberAndSendCodeView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        input_phone_number = request.data.get('phone_number')

        if not email or not input_phone_number:
            return Response({'error': 'Email and phone number are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, username=email)
        if user.phone_number == input_phone_number:
            user.send_verification_code()
            return Response({'message': 'Verification code sent. Please check your phone.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Phone number does not match.'}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({'message': 'Password has been reset successfully.'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Invalid verification code.'}, status=status.HTTP_400_BAD_REQUEST)
