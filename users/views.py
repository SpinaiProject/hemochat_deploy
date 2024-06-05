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
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status, viewsets
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.response import Response

from .serializers import *

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

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

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'code': openapi.Schema(type=openapi.TYPE_STRING, description='카카오로부터 받은 인증 코드'),
        },
        required=['code'],
    ),
    responses={
        200: openapi.Response(
            description='인증에 성공하였습니다.',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'created': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='새 사용자가 생성되었는지 여부'),
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description='JWT 액세스 토큰'),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='JWT 리프레시 토큰'),
                }
            )
        ),
        400: openapi.Response(
            description='잘못된 요청',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지'),
                }
            )
        ),
    },
    operation_description="""
    이 API는 카카오 인증 코드를 사용하여 사용자 인증을 수행합니다.

    **카카오 로그인 로직 설명:**

    1. 프론트엔드에서 카카오 로그인 버튼을 클릭하면 카카오 인증 페이지로 리디렉션됩니다.
    2. 사용자가 카카오 인증을 완료하면, 카카오 서버는 프론트엔드에 인증 코드를 반환합니다.
    3. 프론트엔드는 이 인증 코드를 백엔드의 이 API로 POST 요청을 통해 전달합니다.
       ```json
       {
           "code": "카카오로부터 받은 인증 코드"
       }
       ```
    4. 백엔드는 이 인증 코드를 사용하여 카카오 서버에서 액세스 토큰을 요청합니다.
    5. 받은 액세스 토큰을 사용하여 카카오 사용자 정보를 요청합니다.
    6. 사용자 정보(이메일)를 사용하여 기존 사용자 여부를 확인하고, 없으면 새 사용자를 생성합니다.
    7. JWT 액세스 토큰과 리프레시 토큰을 생성하여 응답합니다.
    """
)
@api_view(['POST'])
@permission_classes([AllowAny])
def kakao_login(request):
    client_id = os.environ.get('KAKAO_REST_API_KEY')
    try:
        data = json.loads(request.body)
        code = data.get('code')
        print(code)
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다. JSON 형식이 올바른지 확인해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    # code로 access token 요청
    token_request = requests.post(
        f"https://kauth.kakao.com/oauth/token?grant_type=authorization_code&client_id={client_id}&redirect_uri={KAKAO_FRONT_REDIRECT}&code={code}",
        headers={"Content-Type": "application/x-www-form-urlencoded;charset=utf-8"},
    )

    try:
        token_response_json = token_request.json()
    except ValueError:
        return JsonResponse({'error': 'Invalid response format'}, status=400)
    print(token_response_json)
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
    access = str(token.access_token)
    refresh = str(token)

    return JsonResponse({
        "created": created,
        "access": access,
        "refresh": refresh
    })


# @swagger_auto_schema(
#     method='post',
#     manual_parameters=[
#         openapi.Parameter(
#             'access',
#             openapi.IN_QUERY,
#             description='액세스 토큰',
#             type=openapi.TYPE_STRING,
#             required=True
#         ),
#     ],
#     responses={
#         200: openapi.Response(
#             description='성공적으로 로그아웃 했습니다',
#             schema=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                 properties={
#                     'message': openapi.Schema(type=openapi.TYPE_STRING, description='성공 메시지'),
#                 }
#             )
#         ),
#         400: openapi.Response(
#             description='잘못된 요청',
#             schema=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                 properties={
#                     'error': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지'),
#                 }
#             )
#         ),
#         401: openapi.Response(
#             description='인증 실패',
#             schema=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                 properties={
#                     'error': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지'),
#                 }
#             )
#         )
#     }
# )
# @api_view(['POST'])
# @permission_classes([IsAuthenticated])  # 헤더에 Authorization': Bearer userToken 형태로 jwt토큰 담아서 요청해야 함
# def kakao_logout(request):
#     access = request.GET.get('access')  # 액세스 토큰을 쿼리 파라미터로 넘겨 받아 로그아웃 하는 방식
#     if not access:
#         return JsonResponse({'error': 'Access token is required'}, status=400)
#
#     headers = {"Authorization": f"Bearer {access}"}
#     logout_response = requests.post("https://kapi.kakao.com/v1/user/logout", headers=headers)
#
#     if logout_response.status_code == 200:
#         return JsonResponse({'message': '성공적으로 로그아웃 했습니다'})  # 200을 받으면, 프론트에서 저장하고있던 jwt토큰을 만료시키고
#         # 홈페이지로 리다이렉트 시켜야함
#     else:
#         return JsonResponse({'error': '로그아웃 실패'}, status=logout_response.status_code)


def test(request):
    scope = "https://www.googleapis.com/auth/userinfo.email"
    client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
    return redirect(
        f"https://accounts.google.com/o/oauth2/v2/auth?client_id={client_id}&redirect_uri={GOOGLE_CALLBACK_URI}&response_type=code&scope={scope}")

@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'code': openapi.Schema(type=openapi.TYPE_STRING, description='Google로부터 받은 인증 코드'),
        },
        required=['code'],
    ),
    responses={
        200: openapi.Response(
            description='성공적으로 인증되었습니다.',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'created': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='새 사용자가 생성되었는지 여부'),
                    'access': openapi.Schema(type=openapi.TYPE_STRING, description='JWT 액세스 토큰'),
                    'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='JWT 리프레시 토큰'),
                }
            )
        ),
        400: openapi.Response(
            description='잘못된 요청',
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, description='에러 메시지'),
                }
            )
        ),
    },
    operation_description = "카카오로그인과 로직 동일. 카카오 명세서 참고"
)
@api_view(['POST'])
def google_login(request):
    client_id = os.environ.get("SOCIAL_AUTH_GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("SOCIAL_AUTH_GOOGLE_SECRET")
    #state = os.environ.get("STATE")
    try:
        data = json.loads(request.body)
        code = data.get('code')
    except json.JSONDecodeError:
        return JsonResponse({'error': '잘못된 요청입니다. JSON 형식이 올바른지 확인해 주세요.'}, status=status.HTTP_400_BAD_REQUEST)

    token_req_data = {
        'client_id': client_id,
        'client_secret': client_secret,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': GOOGLE_CALLBACK_URI
    }
    token_req = requests.post("https://oauth2.googleapis.com/token", data=token_req_data)
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

    @swagger_auto_schema(
        request_body=CustomSignupSerializer,
        responses={
            201: openapi.Response(
                description="성공적으로 회원가입 되었습니다",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING, description="성공 메시지")
                    }
                )
            ),
            400: openapi.Response(
                description="Bad request",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "detail": openapi.Schema(type=openapi.TYPE_STRING, description="에러 메시지")
                    }
                )
            )
        },
        operation_description="이메일을 사용하여 회원가입을 합니다. 비밀번호는 8자이상, 영문자,숫자,특수문자 하나씩을 최소로 포함하고 이들로만 이뤄저야합니다."
    )
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

    @swagger_auto_schema(
        responses={200: DetailSerializer()},
        operation_description="사용자 정보를 조회합니다.",
        security=[{'Bearer': []}]
    )
    def get(self, request, *args, **kwargs):
        user = request.user
        serializer = DetailSerializer(user, context={'request': request})
        return Response(serializer.data)


# 개인정보 업데이트 및 삭제
class UserUpdateView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'profile_image',
                openapi.IN_FORM,
                description="프로필 이미지 파일",
                type=openapi.TYPE_FILE,
                required=True,
            )
        ],
        responses={
            200: openapi.Response(
                description="성공적으로 프로필 사진이 업데이트되었습니다.",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(description='잘못된 요청')
        },
        operation_description="프로필 사진을 업데이트합니다.",
        security=[{'Bearer': []}]
    )
    def patch(self, request, *args, **kwargs):
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': '성공적으로 프로필 사진이 업데이트되었습니다.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        responses={
            204: openapi.Response(description='삭제 완료'),
            404: openapi.Response(description='사용자를 찾을 수 없습니다'),
            500: openapi.Response(description='서버 오류')
        },
        operation_description="사용자 계정을 삭제합니다.",
        security=[{'Bearer': []}]
    )
    def delete(self, request, format=None):
        user = get_object_or_404(User, id=request.user.id)
        try:
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 전화번호 인증 관련 뷰함수(인증번호 발송, 검증)
class SendVerificationCodeAPIView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='전화번호')
            },
            required=['phone_number']
        ),
        responses={
            200: openapi.Response(description='인증 코드가 발송되었습니다.'),
            400: openapi.Response(description='잘못된 요청')
        },
        operation_description="(회원가입 전용. 아이디 비번찾기용 x)전화번호로 인증 코드를 발송합니다."
    )
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        if phone_number is None:
            return Response({'error': '전화번호를 입력해주세요.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        user.send_verification_code()
        return Response({'message': '인증 코드가 발송되었습니다.'}, status=status.HTTP_200_OK)


class VerifyPhoneNumberAPIView(APIView):
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='전화번호'),
                'code': openapi.Schema(type=openapi.TYPE_STRING, description='인증 코드')
            },
            required=['phone_number', 'code']
        ),
        responses={
            200: openapi.Response(description='전화번호가 인증되었습니다.'),
            400: openapi.Response(description='잘못된 요청')
        },
        operation_description="(회원가입 전용. 아이디 비번찾기용 x)인증번호를 받은 전화번호 + 인증 코드로 올바른 인증번호인가 검증"
    )
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

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='전화번호'),
                'username': openapi.Schema(type=openapi.TYPE_STRING, description='이름')
            },
            required=['phone_number','username']
        ),
        responses={
            200: openapi.Response(description='인증 코드가 발송되었습니다.'),
            400: openapi.Response(description='잘못된 요청')
        },
        operation_description="(이메일 찾기 전용) 전화번호로 인증 코드를 발송합니다."
    )
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        username = request.data.get('username')
        if phone_number is None or username is None:
            return Response({'error': '전화번호와 이름이 필요합니다.'}, status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number,username=username)
        user.send_verification_code()
        return Response({'message': '인증 코드가 발송되었습니다.'}, status=status.HTTP_200_OK)


class VerifyPhoneNumberAndReturnEmailAPIView(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='전화번호'),
                'verification_code': openapi.Schema(type=openapi.TYPE_STRING, description='인증 코드')
            },
            required=['phone_number', 'verification_code']
        ),
        responses={
            200: openapi.Response(description='이메일이 반환되었습니다.', schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'email': openapi.Schema(type=openapi.TYPE_STRING, description='사용자의 이메일'),
                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, description='가입일자')
                }
            )),
            400: openapi.Response(description='잘못된 요청')
        },
        operation_description="인증번호 받은 전화번호와 인증 코드를 사용하여 유효한 코드인 경우 이메일을 반환합니다."
    )
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        verification_code = request.data.get('verification_code')
        if phone_number is None or verification_code is None:
            return Response({'error': '전화번호와 인증 코드가 모두 필요합니다.'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = get_object_or_404(User, phone_number=phone_number)
        if user.verify_phone_number(verification_code):
            return Response({'email': user.email,'created_at':user.created_at}, status=status.HTTP_200_OK)
        else:
            return Response({'error': '유효하지 않은 인증 코드입니다.'}, status=status.HTTP_400_BAD_REQUEST)


# 비밀번호 찾기 기능
# class RequestPhoneNumberForPassword(APIView):
#     permission_classes = [AllowAny]
#
#     @swagger_auto_schema(
#         request_body=openapi.Schema(
#             type=openapi.TYPE_OBJECT,
#             properties={
#                 'email': openapi.Schema(type=openapi.TYPE_STRING, description='이메일 주소')
#             },
#             required=['email']
#         ),
#         responses={
#             200: openapi.Response(description='OK'),
#             400: openapi.Response(description='잘못된 요청'),
#             404: openapi.Response(description='사용자를 찾을 수 없습니다')
#         },
#         operation_description="비밀번호 재설정을 위한 전화번호 요청"
#     )
#     def post(self, request, *args, **kwargs):
#         email = request.data.get('email')
#
#         if not email:
#             return Response({'error': '이메일을 입력해주세요'}, status=status.HTTP_400_BAD_REQUEST)
#
#         user = User.objects.filter(email=email, signup_id__isnull=True).first()
#         if user is not None:
#             return Response(status=status.HTTP_200_OK)
#         else:
#             return Response({'error': "사용자를 찾을 수 없습니다. 이메일을 확인하고 다시 시도하십시오."}, status=status.HTTP_404_NOT_FOUND)


class VerifyPhoneNumberForPassword(APIView):
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='이메일 주소'),
                'phone_number': openapi.Schema(type=openapi.TYPE_STRING, description='전화번호')
            },
            required=['email', 'phone_number']
        ),
        responses={
            200: openapi.Response(description='인증 코드가 발송되었습니다. 전화를 확인해 주세요.'),
            400: openapi.Response(description='잘못된 요청'),
            404: openapi.Response(description='사용자를 찾을 수 없습니다')
        },
        operation_description="(비밀번호 찾기 전용) 비밀번호 재설정을 위해 이메일,전화번호로 유저특정하고 그 전화번호로 인증번호 발송"
    )
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

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'email': openapi.Schema(type=openapi.TYPE_STRING, description='이메일 주소'),
                'verification_code': openapi.Schema(type=openapi.TYPE_STRING, description='인증 코드'),
                'new_password': openapi.Schema(type=openapi.TYPE_STRING, description='새 비밀번호')
            },
            required=['email', 'verification_code', 'new_password']
        ),
        responses={
            200: openapi.Response(description='비밀번호가 성공적으로 변경되었습니다.'),
            400: openapi.Response(description='잘못된 요청'),
            404: openapi.Response(description='사용자를 찾을 수 없습니다')
        },
        operation_description="비밀번호 재설정"
    )
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
