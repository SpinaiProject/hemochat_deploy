import json
import os
import time


from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import permission_classes, api_view
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated

from .models import *
from health_records.models import *
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
@permission_classes([IsAuthenticated])
def create_chatroom(request):
    user = request.user
    chatroom = ChatRoom.objects.create(user=user)

    try:
        data = json.loads(request.body)
        health_record_ids = data.get('record_ids', [])
        if not health_record_ids:
            raise ValueError("No health record IDs provided.")

        health_records = HealthRecordImage.objects.filter(id__in=health_record_ids)
        found_ids = health_records.values_list('id', flat=True)
        not_found_ids = set(health_record_ids) - set(found_ids)

        if not_found_ids:
            raise ObjectDoesNotExist(f"HealthRecordImage not found for IDs: {not_found_ids}")

        chatroom.health_records.set(health_records)
    except (ValueError, ObjectDoesNotExist) as e:
        return JsonResponse({
            'message': 'Error processing your request. Please check the provided health record IDs.',
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)

    return JsonResponse({
        'message': 'ChatRoom created successfully with health records.',
        'chatroom_id': str(chatroom.id)
    }, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_chatroom(request, chatroom_id):
    chatroom = get_object_or_404(ChatRoom, id=chatroom_id)

    if chatroom.user != request.user:
        return JsonResponse({
            'message': 'You do not have permission to delete this chatroom.'
        }, status=status.HTTP_403_FORBIDDEN)

    chatroom.delete()
    return JsonResponse({
        'message': 'ChatRoom deleted successfully.'
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


def add_to_cache(chatroom_id, new_qa_pair):
    cache_key = f"chatroom_{chatroom_id}_chat_history"
    current_history_json = cache.get(cache_key, '[]')
    if isinstance(current_history_json, str):
        current_history = json.loads(current_history_json)
    else:
        current_history = current_history_json

    current_history.extend(new_qa_pair)
    cache.set(cache_key, json.dumps(current_history), timeout=3600 * 8)


def save_chat_history(chatroom_id, user_question, complete_answer):
    try:
        chatroom = ChatRoom.objects.get(id=chatroom_id)
        current_history = chatroom.chat_history if chatroom.chat_history else []
        new_qa_pair = [{"role": 'user', "content": user_question}, {"role": 'assistant', "content": complete_answer}]

        current_history.extend(new_qa_pair)
        chatroom.chat_history = current_history
        chatroom.save()

        add_to_cache(chatroom_id, new_qa_pair)
    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'ChatRoom not found'}, status=404)


@require_http_methods(["POST"])
@permission_classes([IsAuthenticated])
def create_stream(request, chatroom_id):
    try:
        decoded_body = request.body.decode('utf-8')
        data = json.loads(decoded_body)
        user_question = data.get('user_question', '')
        ocr_cache_key, chat_history_cache_key = f"chatroom_{chatroom_id}_ocr_texts", f"chatroom_{chatroom_id}_chat_history"
        ocr_texts = cache.get(ocr_cache_key)
        chat_history_json = cache.get(chat_history_cache_key, '[]')  # 캐시에서 chat_history 데이터 가져오기

        if isinstance(chat_history_json, str):
            chat_history = json.loads(chat_history_json)
        else:
            chat_history = chat_history_json
        if ocr_texts is None or chat_history is None:
            chatroom = ChatRoom.objects.get(id=chatroom_id)
            if not ocr_texts:
                print("ocr cache fail")
                ocr_texts = chatroom.health_records.all().values_list('ocr_text', flat=True)
                cache.set(ocr_cache_key, ocr_texts, timeout=3600 * 8)
            if not chat_history:
                print("chat history cache fail")
                chat_history = chatroom.chat_history
                cache.set(chat_history_cache_key, json.dumps(chat_history), timeout=3600 * 8)
        else:
            print("cache hit success:", ocr_texts)
            print("cache hit success:", chat_history, type(chat_history))
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    api_key = os.environ.get('OPEN_AI_API_KEY')
    client = OpenAI(api_key=api_key)
    system_feature = {
        "role": "system",
        "content": f"의료 검사지에 대한 상담을 진행한다. 대화 기록을 토대로 이미 대화한 적 있는 내용에 대해서는 간단히 말해라.\
        반드시 한국말로 답변해라. \
        또한 아래는 유저가 질의하고싶은 건강검사지의 검사내역이다 {ocr_texts}\
        관련질문에 대해 검사내역과 대화 맥락에 기반해 성실히 답변해라"
    }
    # 의료 상담과 무관한 분야에 대한 질문은 반드시 거절해라.
    query = [system_feature]
    if chat_history:
        query.extend(chat_history)
    query.append({"role": "user", "content": user_question})
    print("final query:", query)
    complete_answer = ""

    def event_stream():
        nonlocal complete_answer
        for chunk in client.chat.completions.create(
                model="gpt-4-0613",
                messages=query,
                stream=True,
        ):
            chunk_message = chunk.choices[0].delta.content
            state = chunk.choices[0].finish_reason
            if state == 'stop':
                save_chat_history(chatroom_id, user_question, complete_answer)
                print("user_question:", user_question, "\ncomplete_answer", complete_answer)
                break
            else:
                complete_answer += chunk_message
            yield f"data: {chunk_message}\n\n"

    response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
    response['X-Accel-Buffering'] = 'no'
    response['Cache-Control'] = 'no-cache'
    return response
