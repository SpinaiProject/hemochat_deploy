from django.urls import path, include
from .views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('kakao/login/', kakao_login, name='kakao_login'),
    path('kakao/logout/', kakao_logout, name='kakao_logout'),
    path('kakao/callback/', kakao_callback, name='kakao_callback'),
    path('kakao/login/finish/', KakaoLogin.as_view(), name='kakao_login_todoclass'),
    path('google/login/', google_login, name='google_login'),
    path('google/callback/', google_callback, name='google_callback'),
    path('google/login/finish/', GoogleLogin.as_view(), name='google_login_todjango'),
    path('email/signup/', EmailSignupView.as_view(), name='email_signup'),
    path('email/login/', TokenObtainPairView.as_view(), name='email_login'),
    path('email/login/refresh/', TokenRefreshView.as_view(), name='email_login_refresh'),
    path('email/already_exist/', EmailAlreadyExistAPIView.as_view(), name='email_already_exist'),
    path('my-page/', MyPageView.as_view(), name='my-page'),
    path('user/update/', UserUpdateView.as_view(), name='user_update'),
    path('send-verification-code/', SendVerificationCodeAPIView.as_view(), name='send_verification_code'),
    path('verify-phone-number/', VerifyPhoneNumberAPIView.as_view(), name='verify_phone_number'),
    path('request-phone-number/', RequestPhoneNumberView.as_view(), name='request-phone-number'),
    path('verify-phone-and-send-code/', VerifyPhoneNumberAndSendCodeView.as_view(), name='verify-phone-and-send-code'),
    path('password-reset/', PasswordResetView.as_view(), name='password-reset'),
    path('send-email-verification-code/', SendEmailVerificationCodeAPIView.as_view(),
         name='send-email-verification-code'),
    path('verify-phone-and-return-email/', VerifyPhoneNumberAndReturnEmailAPIView.as_view(),
         name='verify-phone-and-return-email'),
]