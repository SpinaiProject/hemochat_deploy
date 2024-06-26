import datetime
import json
import os

from django.core.cache import cache
from django.http import JsonResponse, StreamingHttpResponse
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.decorators import permission_classes, api_view,parser_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser

from rest_framework.response import Response

from .serializers import *
from health_records.models import *

import openai
from typing_extensions import override
from openai import AssistantEventHandler

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

OPEN_AI_API_KEY = os.environ.get('OPEN_AI_API_KEY')
assistant_id = os.environ.get('OPEN_AI_ASSISTANT_ID')
OPEN_AI_CHAT_INSTRUCTION = os.environ.get('OPEN_AI_CHAT_INSTRUCTION')
client = openai.OpenAI(api_key=OPEN_AI_API_KEY)

ALLOWED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png']
MAX_IMAGE_SIZE_MB = 5


# @swagger_auto_schema(
#     method='post',
#     responses={
#         201: openapi.Response(
#             description="채팅방이 성공적으로 생성되었습니다.",
#             schema=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                 properties={
#                     'chatroom_id': openapi.Schema(type=openapi.TYPE_STRING, description='생성된 채팅방 ID')
#                 }
#             )
#         ),
#         500: openapi.Response(description="Internal server error")
#     },
#     operation_description="(체험페이지 전용) 비로그인 상태로 체험형 채팅방을 생성합니다. 체험하기 버튼"
# )
# @api_view(['POST'])
# @permission_classes([AllowAny])
# def create_temp_chatroom(request):
#     try:
#         empty_chatroom = client.beta.threads.create()
#         chatroom = TempChatroom.objects.create(
#             chatroom_id=empty_chatroom.id
#         )
#         return Response({
#             'chatroom_id': chatroom.chatroom_id,
#         }, status=status.HTTP_201_CREATED)
#     except Exception as e:
#         return Response({
#             'error': 'An unexpected error occurred: {}'.format(str(e))
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
#
#
# def validate_image(image: UploadedFile):
#     ext = os.path.splitext(image.name)[1].lower()
#     if ext not in ALLOWED_IMAGE_EXTENSIONS:
#         raise ValidationError('Unsupported file extension.')
#
#     if image.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
#         raise ValidationError('File size exceeds the allowed limit of 5MB.')
#
#     valid_mime_types = ['image/jpeg', 'image/png', 'image/gif']
#     if image.content_type not in valid_mime_types:
#         raise ValidationError('Unsupported file type.')
#
#
# @swagger_auto_schema(
#     method='post',
#     manual_parameters=[
#         openapi.Parameter(
#             'chatroom_id',
#             openapi.IN_PATH,
#             description="채팅방 ID",
#             type=openapi.TYPE_STRING,
#             required=True
#         ),
#         openapi.Parameter(
#             'image',
#             openapi.IN_FORM,
#             description="업로드할 이미지 파일",
#             type=openapi.TYPE_FILE,
#             required=True
#         ),
#     ],
#     responses={
#         200: openapi.Response(
#             description="이미지가 정상적으로 업로드되었습니다.",
#             schema=openapi.Schema(
#                 type=openapi.TYPE_OBJECT,
#                 properties={
#                     'chatroom_id': openapi.Schema(type=openapi.TYPE_STRING, description='채팅방 ID'),
#                     'image_url': openapi.Schema(type=openapi.TYPE_STRING, description='이미지 URL')
#                 }
#             )
#         ),
#         400: openapi.Response(description="Bad request"),
#         404: openapi.Response(description="Chatroom not found"),
#         500: openapi.Response(description="Internal server error")
#     },
#     operation_description="임시 채팅방에 이미지를 업로드합니다."
# )
# @api_view(['POST'])
# @permission_classes([AllowAny])
# @parser_classes([MultiPartParser, FormParser])
# def upload_temp_image(request, chatroom_id):
#     try:
#         chatroom = TempChatroom.objects.get(chatroom_id=chatroom_id)
#         if 'image' not in request.FILES:
#             return Response({'error': 'No image file provided'}, status=status.HTTP_400_BAD_REQUEST)
#
#         image = request.FILES['image']
#
#         try:
#             validate_image(image)
#         except ValidationError as e:
#             return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#         chatroom.image = image
#         chatroom.save()
#
#         return Response({
#             'chatroom_id': chatroom.chatroom_id,
#             'image_url': chatroom.image.url if chatroom.image else None
#         }, status=status.HTTP_200_OK)
#
#     except TempChatroom.DoesNotExist:
#         return Response({'error': 'Chatroom not found'}, status=status.HTTP_404_NOT_FOUND)
#     except Exception as e:
#         return Response({'error': f'An error occurred while updating the image: {str(e)}'},
#                         status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@swagger_auto_schema(
    method='post',
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'record_ids': openapi.Schema(
                type=openapi.TYPE_ARRAY,
                items=openapi.Items(type=openapi.TYPE_INTEGER),
                description="선택한 건강 기록 이미지의 ID 목록"
            ),
            'title': openapi.Schema(type=openapi.TYPE_STRING, description="채팅방 제목"),
        },
        required=['record_ids', 'title'],
    ),
    responses={
        200: openapi.Response(
            description="채팅방이 생성되었습니다.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'message': openapi.Schema(type=openapi.TYPE_STRING, description='성공 메시지'),
                    'thread_id': openapi.Schema(type=openapi.TYPE_STRING, description='생성된 채팅방 ID')
                }
            )
        ),
        400: openapi.Response(description="Bad request"),
        403: openapi.Response(description="Forbidden"),
        500: openapi.Response(description="Internal server error")
    },
    operation_description="""
    새로운 채팅방을 생성하고 그 채팅방 ID를 발급받는 API입니다. (체험형, 가입자용 공용)
    리스폰스에 담긴 채팅방 ID는 이후 채팅방 입장, 삭제, 메시지 전송 API 사용 시 경로 변수로 URL에 첨부해서 채팅방을 특정하는 데 사용합니다.

    [리퀘스트 바디]
    - 체험형 채팅방인 경우: record_ids는 로그인 유저의 경우 로그인된 유저의 이미지 ID 목록을, 비로그인 유저의 경우 null로 설정합니다.
    - title: 채팅방 제목은 반드시 입력해야 합니다.

    [헤더에 JWT 인증 토큰]
    - 체험판 페이지에서는 부착할 필요 없고, 로그인 전용 페이지에서 시도하는 경우 붙여주세요.
    - JWT 토큰을 'Authorization: Bearer {토큰}' 형태로 헤더에 담아야 합니다.
    """
)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_chatroom(request):
    try:
        user = request.user if request.user.is_authenticated else None
        data = json.loads(request.body)
        record_ids = data.get('record_ids')
        title = data.get('title')

        if not title:
            return Response({"error": "채팅방 제목을 기입하세요."}, status=400)

        records = HealthRecordImage.objects.filter(pk__in=record_ids)
        if not records.exists():
            return Response({"error": "이미지를 선택하지 않았거나 존재하지 않는 이미지입니다."}, status=400)

        for record in records:
            if user:
                if record.user and record.user != user:
                    return Response({"error": "로그인한 사용자가 소유하지 않은 이미지가 포함되어 있습니다."}, status=403)
                if not record.user:
                    return Response({"error": "로그인 사용자는 비로그인 사용자의 이미지를 사용할 수 없습니다."}, status=403)
            else:
                if record.user:
                    return Response({"error": "비로그인 사용자는 로그인된 사용자의 이미지를 사용할 수 없습니다."}, status=403)

        init_messages = [{"role": "assistant", "content": OPEN_AI_CHAT_INSTRUCTION}]
        for record in records:
            if not record.ocr_text.strip():
                return Response({"error": "AI분석을 하지 않은 이미지가 포함되어 있습니다. 먼저 이미지 분석을 수행하세요."}, status=400)
            init_messages.append({"role": "assistant", "content": record.ocr_text})

        empty_chatroom = client.beta.threads.create(messages=init_messages)

        chatroom_data = {
            'chatroom_id': empty_chatroom.id,
            'title': title,
            'is_temporary': not user  # 비로그인 사용자의 경우 임시 채팅방으로 표시
        }

        if user:
            chatroom_data['user'] = user

        chatroom = ChatRoom.objects.create(**chatroom_data)
        chatroom.health_records.set(records)

        update_chatroom_cache_on_create(user.id if user else None, chatroom, records)

        return Response({
            "message": "채팅방이 생성되었습니다",
            "thread_id": chatroom.chatroom_id
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)


def update_chatroom_cache_on_create(user_id, chatroom, records):
    cache_key = f"user_{user_id}_chatrooms"
    representative_image = records.first().image.url if records.exists() else None

    chatroom_data = {
        "chatroom_id": chatroom.chatroom_id,
        "title": chatroom.title,
        "updated_at": chatroom.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
        "representative_image": representative_image
    }

    cached_data = cache.get(cache_key)
    if cached_data:
        data = json.loads(cached_data)
        data.append(chatroom_data)
        cache.set(cache_key, json.dumps(data), timeout=900)
    else:
        cache.set(cache_key, json.dumps([chatroom_data]), timeout=900)


@swagger_auto_schema(
    method='post',
    responses={
        200: openapi.Response(
            description="사용자의 채팅방 목록",
            schema=ChatRoomListSerializer(many=True)
        ),
        400: openapi.Response(description="Bad request")
    },
    operation_description="""사용자의 채팅방 목록을 반환합니다.
    [경로 파라미터]
    채팅방 ID를 경로 파라미터로 사용해 채팅방을 특정합니다.
    
    [헤더에 jwt 인증 토큰]
     로그인 전제이므로 jwt 토큰을 'Authorization: Bearer {토큰}'형태로 헤더에 담아야합니다."""
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def list_chatroom(request):
    try:
        user = request.user
        cache_key = f"user_{user.id}_chatrooms"
        cached_chatrooms = cache.get(cache_key)
        if cached_chatrooms:
            return Response(json.loads(cached_chatrooms))

        chatrooms = user.chatrooms.all()
        serializer = ChatRoomListSerializer(chatrooms, many=True)
        cache.set(cache_key, json.dumps(serializer.data), timeout=600)

        return Response(serializer.data)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


@swagger_auto_schema(
    method='get',
    manual_parameters=[
        openapi.Parameter(
            'chatroom_id',
            openapi.IN_PATH,
            description="상세 정보를 조회할 채팅방의 ID",
            type=openapi.TYPE_STRING
        )
    ],
    responses={
        200: openapi.Response(
            description="채팅방 세부 정보와 최근 메시지가 성공적으로 조회되었습니다.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'chatroom': openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'id': openapi.Schema(type=openapi.TYPE_INTEGER),
                            'title': openapi.Schema(type=openapi.TYPE_STRING),
                            'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            'health_records': openapi.Schema(
                                type=openapi.TYPE_ARRAY,
                                items=openapi.Schema(
                                    type=openapi.TYPE_OBJECT,
                                    properties={
                                        'user': openapi.Schema(type=openapi.TYPE_INTEGER),
                                        'image': openapi.Schema(type=openapi.TYPE_STRING, format='binary'),
                                        'ocr_text': openapi.Schema(type=openapi.TYPE_STRING),
                                        'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                                    }
                                )
                            )
                        }
                    ),
                    'messages': openapi.Schema(
                        type=openapi.TYPE_ARRAY,
                        items=openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                'role': openapi.Schema(type=openapi.TYPE_STRING),
                                'text': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    )
                }
            )
        ),
        404: openapi.Response(
            description="존재하지 않는 채팅방입니다.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, example='존재하지 않는 채팅방입니다')
                }
            )
        ),
        500: openapi.Response(
            description="예기치 않은 오류가 발생했습니다.",
            schema=openapi.Schema(
                type=openapi.TYPE_OBJECT,
                properties={
                    'error': openapi.Schema(type=openapi.TYPE_STRING, example='Internal server error message')
                }
            )
        )
    },
    operation_description="""채팅방 입장 시 사용합니다. 채팅방의 상세 정보와 메시지 내역을 조회합니다.
    [경로 파라미터]
    채팅방 ID를 경로 파라미터로 사용해 채팅방을 특정합니다.
    
    [헤더에 jwt인증토큰]
    서버측에서는 특정된 채팅방이 체험용인지, 정규가입자의 것인지 식별해냅니다.
    정규가입자의 것인 경우에는 로그인 전제이므로 jwt 토큰을 'Authorization: Bearer {토큰}'형태로 헤더에 담을 것을 요구합니다.
    체험용은 jwt 토큰 필요없습니다.
    """
)
@api_view(['GET'])
@permission_classes([AllowAny])
def enter_chatroom(request, chatroom_id):
    try:
        user = request.user if request.user.is_authenticated else None
        chatroom = get_object_or_404(ChatRoom, chatroom_id=chatroom_id)
        if not chatroom.is_temporary and not user:
            return Response({"error": "Authentication credentials were not provided."}, status=401)

        cache_key = f"chatroom_{chatroom_id}_details"
        cached_data = cache.get(cache_key)
        if cached_data:
            return Response(json.loads(cached_data))

        serializer = ChatRoomDetailSerializer(chatroom, context={'request': request})
        thread_messages = client.beta.threads.messages.list(chatroom.chatroom_id)
        total_messages = []
        user_message_found = False

        for message in reversed(list(thread_messages)):
            if message.role == 'user':
                user_message_found = True

            if user_message_found:
                for content_block in message.content:
                    created_at_datetime = datetime.datetime.fromtimestamp(message.created_at)
                    formatted_created_at = created_at_datetime.strftime('%Y-%m-%d %H:%M:%S')
                    total_messages.append({
                        "created_at": formatted_created_at,
                        "role": message.role,
                        "text": content_block.text.value
                    })

        response_data = {
            'chatroom': serializer.data,
            'messages': total_messages
        }
        cache.set(cache_key, json.dumps(response_data), timeout=900)
        return Response(response_data)
    except ChatRoom.DoesNotExist:
        return Response({'error': '존재하지 않는 채팅방입니다'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@swagger_auto_schema(
    method='delete',
    manual_parameters=[
        openapi.Parameter(
            'chatroom_id',
            openapi.IN_PATH,
            description="채팅방 ID",
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    responses={
        204: openapi.Response(description="채팅방이 삭제되었습니다"),
        400: openapi.Response(description="Bad request"),
        404: openapi.Response(description="존재하지 않거나 삭제 권한이 없는 채팅방입니다."),
        500: openapi.Response(description="Internal server error")
    },
    operation_description="""채팅방을 삭제합니다.
    
     [경로 파라미터]
     채팅방 ID를 경로 파라미터로 사용해 채팅방을 특정합니다.
    
     [헤더에 jwt 인증 토큰]
     로그인 전제이므로 jwt 토큰을 'Authorization: Bearer {토큰}'형태로 헤더에 담아야합니다."""
)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_chatroom(request, chatroom_id):
    global client
    try:
        user = request.user
        chatroom = user.chatrooms.get(chatroom_id=chatroom_id)
        client = openai.OpenAI(api_key=OPEN_AI_API_KEY)
        success = client.beta.threads.delete(chatroom.chatroom_id)
        if success:
            chatroom.delete()
            cache.delete(f"user_{user.id}_chatrooms")
            cache.delete(f"chatroom_{chatroom_id}_details")
            return Response({'message': '채팅방이 삭제되었습니다'}, status=204)
        else:
            return Response({'message': '채팅방 삭제 실패'}, status=400)
    except ChatRoom.DoesNotExist:
        return Response({'error': '존재하지 않거나 삭제 권한이 없는 채팅방입니다.'}, status=404)
    except Exception as e:
        return Response({'error': str(e)}, status=400)


class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)


def update_chatroom_cache(chatroom_id, content, accumulated_responses):
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_user_message = {
        "created_at": current_time,
        "role": "user",
        "text": content
    }

    new_system_message = {
        "created_at": current_time,
        "role": "assistant",
        "text": " ".join(accumulated_responses)
    }

    cache_key = f"chatroom_{chatroom_id}_details"
    cached_data = cache.get(cache_key)
    if cached_data:
        data = json.loads(cached_data)
        data['messages'].extend([new_user_message, new_system_message])
        cache.set(cache_key, json.dumps(data), timeout=900)

@swagger_auto_schema(
    method='post',
    manual_parameters=[
        openapi.Parameter(
            'chatroom_id',
            openapi.IN_PATH,
            description="채팅방 ID",
            type=openapi.TYPE_STRING,
            required=True
        )
    ],
    request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'content': openapi.Schema(type=openapi.TYPE_STRING, description="메시지 내용"),
        },
        required=['content']
    ),
    responses={
        200: openapi.Response(
            description="메시지가 성공적으로 생성되었습니다.",
            schema=openapi.Schema(
                type=openapi.TYPE_STRING,
                description="스트리밍된 메시지 응답"
            )
        ),
        400: openapi.Response(description="Bad request"),
        401: openapi.Response(description="Authentication credentials were not provided."),
        500: openapi.Response(description="Internal server error")
    },
    operation_description="""
    AI에게 질문을 보내고 chatgpt응답과 같이 스트리밍된 응답을 반환하는 중요한 api입니다.
    [UI 요구사항]
    AI 응답이 완료되기 전까지, 재차 이 질문 API를 사용할 수 없도록, 질문 전송버튼을 비활성화해주세요.
    
    [경로 파라미터]
    채팅방 ID를 경로 파라미터로 사용해 어느 채팅방에서 질문을 전송하고자 하는지 특정합니다.
    
    [헤더에 jwt 인증 토큰]
    서버측에서는 특정된 채팅방이 체험용인지, 정규가입자의 것인지 식별해냅니다.
    정규가입자의 것인 경우에는 로그인 전제이므로 jwt 토큰을 'Authorization: Bearer {토큰}'형태로 헤더에 담을 것을 요구합니다.
    체험용은 jwt 토큰 필요없습니다.
    
    [참고]
    체험용 채팅방인 경우, 메시지를 보낼 때마다 채팅횟수가 증가하고, 5회 초과시 메시지 전송을 서버측에서 거부합니다.
    """
)
@api_view(['POST'])
@permission_classes([AllowAny])
def create_message(request, chatroom_id):
    content = request.data.get("content")
    chatroom = get_object_or_404(ChatRoom, chatroom_id=chatroom_id)

    if not request.user.is_authenticated and not chatroom.is_temporary:
        return Response({"error": "Authentication credentials were not provided."}, status=401)

    def event_stream():
        accumulated_responses = []

        try:
            message = client.beta.threads.messages.create(
                thread_id=chatroom_id,
                role="user",
                content=content,
            )

            with client.beta.threads.runs.stream(
                    thread_id=chatroom_id,
                    assistant_id=assistant_id,
                    instructions=content,
                    event_handler=EventHandler(),
            ) as stream:
                for event in stream:
                    if event.event == 'thread.message.delta':
                        text_value = event.data.delta.content[0].text.value
                        accumulated_responses.append(text_value)
                        yield f"data: {json.dumps(text_value, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
        finally:
            if accumulated_responses:
                update_chatroom_cache(chatroom_id, content, accumulated_responses)
            if chatroom.is_temporary:
                try:
                    chatroom.chat_num += 1
                    chatroom.save()
                except ValidationError as ve:
                    yield f"data: {{\"error\": \"{str(ve)}\"}}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    return response

# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def create_chatroom(request):
#     user = request.user
#     chatroom = ChatRoom.objects.create(user=user)
#
#     try:
#         data = json.loads(request.body)
#         health_record_ids = data.get('record_ids', [])
#         if not health_record_ids:
#             raise ValueError("No record IDs provided.")
#
#         health_records = HealthRecordImage.objects.filter(id__in=health_record_ids)
#         found_ids = health_records.values_list('id', flat=True)
#         not_found_ids = set(health_record_ids) - set(found_ids)
#
#         if not_found_ids:
#             raise ObjectDoesNotExist(f"HealthRecordImage not found for IDs: {not_found_ids}")
#
#         chatroom.health_records.set(health_records)
#     except (ValueError, ObjectDoesNotExist) as e:
#         return JsonResponse({
#             'message': 'Error processing your request. Please check the provided health record IDs.',
#             'error': str(e)
#         }, status=status.HTTP_400_BAD_REQUEST)
#
#     return JsonResponse({
#         'message': 'ChatRoom created successfully with health records.',
#         'chatroom_id': str(chatroom.id)
#     }, status=status.HTTP_200_OK)


# @api_view(['DELETE'])
# @permission_classes([IsAuthenticated])
# def delete_chatroom(request, chatroom_id):
#     chatroom = get_object_or_404(ChatRoom, id=chatroom_id)
#
#     if chatroom.user != request.user:
#         return JsonResponse({
#             'message': 'You do not have permission to delete this chatroom.'
#         }, status=status.HTTP_403_FORBIDDEN)
#
#     chatroom.delete()
#     return JsonResponse({
#         'message': 'ChatRoom deleted successfully.'
#     }, status=status.HTTP_200_OK)


# def cache_chatroom_data(chatroom_id, new_qa_pair=None):
#     ocr_cache_key = f"chatroom_{chatroom_id}_ocr_texts"
#     chat_history_cache_key = f"chatroom_{chatroom_id}_chat_history"
#
#     ocr_texts = cache.get(ocr_cache_key)
#     chat_history_json = cache.get(chat_history_cache_key)
#
#     try:
#         chatroom = ChatRoom.objects.get(id=chatroom_id)
#
#         if not ocr_texts:
#             ocr_texts = list(chatroom.health_records.all().values_list('ocr_text', flat=True))
#             cache.set(ocr_cache_key, ocr_texts, timeout=600)
#
#         if chat_history_json is None:
#             chat_history = chatroom.chat_history if chatroom.chat_history else []
#             print("read from db or new: ", chat_history, type(chat_history))
#             print("dumped and cached: ", json.dumps(chat_history, ensure_ascii=False),
#                   type(json.dumps(chat_history, ensure_ascii=False)))
#             cache.set(chat_history_cache_key, json.dumps(chat_history, ensure_ascii=False), timeout=600)
#         else:
#             print("before loading: ", chat_history_json, type(chat_history_json))
#             chat_history = json.loads(chat_history_json)
#             print("loaded to python dictionary list: ", chat_history, type(chat_history))
#
#     except ObjectDoesNotExist:
#         return None, None
#
#     if new_qa_pair:
#         print("before extend: ", chat_history, type(chat_history))
#         chat_history.extend(new_qa_pair)
#         print("new_qa_pair: ", new_qa_pair, type(new_qa_pair))
#         print("appended new chat: ", chat_history, type(chat_history))
#         print("dumped and cached: ", json.dumps(chat_history, ensure_ascii=False),
#               type(json.dumps(chat_history, ensure_ascii=False)))
#         cache.set(chat_history_cache_key, json.dumps(chat_history, ensure_ascii=False), timeout=600)
#
#     return ocr_texts, chat_history

# class CustomJsonResponse(JsonResponse):
#     def __init__(self, data, encoder=json.JSONEncoder, safe=True, json_dumps_params=None, **kwargs):
#         if json_dumps_params is None:
#             json_dumps_params = {}
#         json_dumps_params["ensure_ascii"] = False
#         super().__init__(data, encoder=encoder, safe=safe, json_dumps_params=json_dumps_params, **kwargs)

# @api_view(['GET'])
# @permission_classes([IsAuthenticated])
# def enter_chatroom(request, chatroom_id):
#     try:
#         chatroom = ChatRoom.objects.get(pk=chatroom_id)
#         if chatroom.entered:
#             return JsonResponse({'error': 'cannot enter while entered'}, status=403)
#         serializer = ChatRoomSerializer(chatroom)
#
#         cache_chatroom_data(chatroom_id)
#
#         chatroom.last_entered = timezone.now()
#         chatroom.entered = True
#         chatroom.leaved = False
#         chatroom.save(update_fields=['last_entered'])
#
#         return CustomJsonResponse(serializer.data, safe=False)
#     except ChatRoom.DoesNotExist:
#         return JsonResponse({'error': 'ChatRoom not found'}, status=404)


