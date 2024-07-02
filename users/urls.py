from django.urls import path, include
from .views import *
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('kakao/login/', kakao_login, name='kakao_login'),
    path('google/login/', google_login, name='google_login'),

    path('email/signup/', EmailSignupView.as_view(), name='email_signup'),
    path('email/duplicate/',EmailCheckView.as_view() , name='email_duplicate'),
    path('email/login/', TokenObtainPairView.as_view(), name='email_login'),
    path('email/send-verification-code/', SendVerificationCodeAPIView.as_view(), name='send_verification_code'),
    path('email/verify-phone-number/', VerifyPhoneNumberAPIView.as_view(), name='verify_phone_number'),

    path('my-page/', MyPageView.as_view(), name='my-page'),
    path('user/update/', UserUpdateView.as_view(), name='user_update'),
    path('user/delete/', UserDeleteView.as_view(), name='user_delete'),
    path('user/refresh/', TokenRefreshView.as_view(), name='refresh'),

    path('find-email/send-verification-code/', SendEmailVerificationCodeAPIView.as_view(),
         name='find-email-verification-code'),
    path('find-email/return/', VerifyPhoneNumberAndReturnEmailAPIView.as_view(),
         name='find-email-return'),

    path('find-password/send-verification-code/', SendPhoneNumberForPassword.as_view(), name='pwd_send_verification_code'),
    path('find-password/verify-verification-code/', VerifyVerificationCodeView.as_view(), name='pwd_verify_code'),
    path('find-password/reset/', PasswordResetView.as_view(), name='reset-password'),

]