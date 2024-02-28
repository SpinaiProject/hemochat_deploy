from django.urls import path, include
from .views import *

urlpatterns = [
    path('kakao/login/', kakao_login, name='kakao_login'),
    path('kakao/logout/', kakao_logout, name='kakao_logout'),
    path('kakao/callback/', kakao_callback, name='kakao_callback'),
    path('kakao/login/finish/', KakaoLogin.as_view(), name='kakao_login_todoclass'),
    path('google/login/', google_login, name='google_login'),
    path('google/callback/', google_callback, name='google_callback'),
    path('google/login/finish/', GoogleLogin.as_view(), name='google_login_todjango'),
]