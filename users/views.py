import os
import requests
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from allauth.socialaccount.providers.kakao import views as kakao_view
from allauth.socialaccount.models import SocialAccount
from dj_rest_auth.registration.views import SocialLoginView
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.conf import settings
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated

from .serializers import *
from rest_framework import status, viewsets

BASE_URL = settings.BASE_URL
KAKAO_CALLBACK_URI = settings.BASE_URL + 'api/users/kakao/callback/'
KAKAO_FINISH_URI = settings.BASE_URL + 'api/users/kakao/login/finish/'


class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = User.objects.all()
    serializer_class = DetailSerializer


def kakao_login(request):
    client_id = os.environ.get("KAKAO_REST_API_KEY")
    return redirect(
        f"https://kauth.kakao.com/oauth/authorize?client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&response_type=code&scope=account_email")


def kakao_callback(request):
    client_id = os.environ.get('KAKAO_REST_API_KEY')
    code = request.GET.get('code')
    # print(code)

    # code로 access token 요청
    token_request = requests.post(
        f"https://kauth.kakao.com/oauth/token?grant_type=authorization_code&client_id={client_id}&redirect_uri={KAKAO_CALLBACK_URI}&code={code}",
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )

    try:
        token_response_json = token_request.json()
    except ValueError:  # JSON 형식이 아닌 경우 에러 처리
        return JsonResponse({'error': 'Invalid response format'}, status=400)

    # print("response=>", token_response_json)

    # 에러 발생 시 중단
    error = token_response_json.get("error", None)
    if error is not None:
        return JsonResponse({'error': error}, status=400)

    # access token으로 카카오톡 프로필 요청
    access_token = token_response_json.get("access_token")
    print("access_token: " + str(access_token))
    profile_request = requests.post(
        "https://kapi.kakao.com/v2/user/me",
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )
    profile_json = profile_request.json()
    kakao_account = profile_json.get("kakao_account")
    username = kakao_account.get("name", None)

    try:
        # 전달받은 닉네임으로 등록된 유저가 있는지 탐색
        user = User.objects.get(username=username)
        # FK로 연결되어 있는 socialaccount 테이블에서 해당 닉네임의 유저가 있는지 확인
        social_user = SocialAccount.objects.get(user=user)

        # 있는데 카카오계정이 아니어도 에러
        if social_user.provider != 'kakao':
            return JsonResponse({'err_msg': 'no matching social type'}, status=status.HTTP_400_BAD_REQUEST)

        # 이미 카카오로 제대로 가입된 유저 => 로그인 & 해당 유저의 jwt 발급
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(KAKAO_FINISH_URI, data=data)
        accept_status = accept.status_code

        # print("accept=>", accept)
        if accept_status != 200:
            return JsonResponse({'err_msg': 'failed to signin'}, status=accept_status)

        accept_json = accept.json()
        print("jwt_token1: " + str(accept_json))
        return JsonResponse(accept_json)

    except User.DoesNotExist:
        # 전달받은 닉네임으로 기존에 가입된 유저가 아예 없으면 => 새로 회원가입 & 해당 유저의 jwt 발급
        data = {'access_token': access_token, 'code': code}
        accept = requests.post(KAKAO_FINISH_URI, data=data)
        accept_status = accept.status_code

        # print("accept=>", accept)
        if accept_status != 200:
            return JsonResponse({'err_msg': 'failed to signup'}, status=accept_status)
        accept_json = accept.json()
        print("jwt_token2: " + str(accept_json))
        return JsonResponse(accept_json)

    except SocialAccount.DoesNotExist:
        # User는 있는데 SocialAccount가 없을 때
        return JsonResponse({'err_msg': 'username exists but not social user'}, status=status.HTTP_400_BAD_REQUEST)


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
