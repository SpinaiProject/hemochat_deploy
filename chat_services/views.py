import json
import os
import time

from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated

from .models import *
from .serializers import ChatRoomSerializer

from openai import OpenAI
import openai


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_assistant_config(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({"error": "User is not authenticated."}, status=401)
    api_key = os.environ.get('OPEN_AI_API_KEY')
    client = OpenAI(api_key=api_key)

    if not api_key:
        return JsonResponse({"error": "API key is missing."}, status=400)
    try:
        name = "의료 상담 전문 채팅앱"
        my_assistant = client.beta.assistants.create(
            instructions="""제공받은 의료검사 정보를 분석하고 검색하여, 해당 건강 수치들이 정상 범위 내에 있는지 확인합니다.
정상 범위를 벗어난 경우 필요한 의학적 조치를 한국어로 상담해주며, 수치에 대한 의학적 정보에 대한 질의가 있을 때는
그에 대한 상세한 개념 설명을 제공합니다. 모든 상담은 한국어로 진행됩니다.""",
            name="name",
            tools=[{"type": "retrieval"}],
            model="gpt-4-turbo-preview",
        )

    except Exception as e:
        return JsonResponse({"error": f"Unexpected error: {str(e)}"}, status=500)

    try:
        assistant_config = AssistantConfig.objects.create(
            user=user,
            name=name,
            api_key=api_key,
            model="gpt-4",
            active=True
        )
    except Exception as e:
        return JsonResponse({"error": f"Database error: {str(e)}"}, status=500)

    return JsonResponse({
        "message": "Assistant Config Successfully Created.",
        "assistant_id": my_assistant.id
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_thread(request):
    try:
        user = request.user

        api_key = os.environ.get('OPEN_AI_API_KEY')
        if not api_key:
            return JsonResponse({"error": "API key is missing."}, status=400)

        client = openai.OpenAI(api_key=api_key)
        empty_thread = client.beta.threads.create()
        chat_thread = ChatThread.objects.create(
            user=user,
            thread_id=empty_thread.id
        )

        return JsonResponse({
            "message": "Chat Thread Successfully Created.",
            "thread_id": chat_thread.thread_id
        })
    except KeyError:
        return JsonResponse({"error": "Failed to create chat thread due to missing data from OpenAI response"},
                            status=500)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_message(request):
    if request.method == "POST":
        api_key = os.environ.get('OPEN_AI_API_KEY')
        client = OpenAI(api_key=api_key)
        thread_id = request.POST.get("thread_id")
        content = request.POST.get("content")

        try:
            message = client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content,
            )

            assistant_id = request.POST.get("assistant_id")
            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=assistant_id
            )
            run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

            while True:
                if run.status == "completed":
                    break
                run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                print(run)
                time.sleep(1)

            messages = client.beta.threads.messages.list(thread_id=thread_id)

            return JsonResponse({
                "message": "Message successfully created.",
                "thread_question": content,
                "thread_answer": messages.data[0].content[0].text.value
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid request method."}, status=400)


# @require_http_methods(["POST"])
# def create_run(request):
#     api_key = os.environ.get('OPEN_AI_API_KEY')
#     client = OpenAI(api_key=api_key)
#     thread_id = request.POST.get("thread_id")
#     assistant_id = request.POST.get("assistant_id")
#
#     if not thread_id or not assistant_id:
#         return JsonResponse({"error": "Missing thread_id or assistant_id"}, status=400)
#
#     try:
#         run = client.beta.threads.runs.create(
#             thread_id=thread_id,
#             assistant_id=assistant_id
#         )
#
#         return JsonResponse({
#             "status": "success",
#             "data": run
#         })
#     except Exception as e:
#         return JsonResponse({
#             "status": "error",
#             "message": str(e)
#         }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated]) # 어느 검사지에 대해 채팅할 것인지에 대한 정보 추가 필요
def create_chatroom(request):
    user = request.user
    chatroom = ChatRoom.objects.create(user=user)

    return JsonResponse({
        'message': 'ChatRoom created successfully.',
        'chatroom_id': str(chatroom.id)
    }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chatroom_detail_view(request, pk):
    try:
        chatroom = ChatRoom.objects.get(pk=pk)
        serializer = ChatRoomSerializer(chatroom)
        return JsonResponse(serializer.data, safe=False)
    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'ChatRoom not found'}, status=404)


