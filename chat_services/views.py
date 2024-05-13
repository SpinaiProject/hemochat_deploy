import datetime
import json
import os

from django.core.cache import cache
from django.http import JsonResponse, StreamingHttpResponse
from rest_framework.decorators import permission_classes, api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .serializers import *
from health_records.models import *

import openai
from typing_extensions import override
from openai import AssistantEventHandler

OPEN_AI_API_KEY = os.environ.get('OPEN_AI_API_KEY')
OPEN_AI_ASSISTANT_ID = os.environ.get('OPEN_AI_ASSISTANT_ID')
OPEN_AI_CHAT_INSTRUCTION = os.environ.get('OPEN_AI_CHAT_INSTRUCTION')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chatroom(request):
    try:
        user = request.user
        client = openai.OpenAI(api_key=OPEN_AI_API_KEY)

        data = json.loads(request.body)
        record_ids = data.get('record_ids')
        title = data.get('title')
        if not title:
            return Response({"error": "채팅방 제목을 기입하세요."}, status=400)
        records = HealthRecordImage.objects.filter(pk__in=record_ids)
        if not records.exists():
            return Response({"error": "이미지를 선택하지 않았거나 존재하지 않는 이미지입니다."}, status=400)

        init_messages = [{"role": "assistant", "content": OPEN_AI_CHAT_INSTRUCTION}]
        init_messages.extend([{"role": "user", "content": record.ocr_text} for record in records])
        empty_chatroom = client.beta.threads.create(messages=init_messages)
        chatroom = ChatRoom.objects.create(
            user=user,
            chatroom_id=empty_chatroom.id,
            title=title
        )
        chatroom.health_records.set(records)

        update_chatroom_cache_on_create(user.id, chatroom, records)

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
            raise ValueError("No record IDs provided.")

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


def cache_chatroom_data(chatroom_id, new_qa_pair=None):
    ocr_cache_key = f"chatroom_{chatroom_id}_ocr_texts"
    chat_history_cache_key = f"chatroom_{chatroom_id}_chat_history"

    ocr_texts = cache.get(ocr_cache_key)
    chat_history_json = cache.get(chat_history_cache_key)

    try:
        chatroom = ChatRoom.objects.get(id=chatroom_id)

        if not ocr_texts:
            ocr_texts = list(chatroom.health_records.all().values_list('ocr_text', flat=True))
            cache.set(ocr_cache_key, ocr_texts, timeout=600)

        if chat_history_json is None:
            chat_history = chatroom.chat_history if chatroom.chat_history else []
            print("read from db or new: ", chat_history, type(chat_history))
            print("dumped and cached: ", json.dumps(chat_history, ensure_ascii=False),
                  type(json.dumps(chat_history, ensure_ascii=False)))
            cache.set(chat_history_cache_key, json.dumps(chat_history, ensure_ascii=False), timeout=600)
        else:
            print("before loading: ", chat_history_json, type(chat_history_json))
            chat_history = json.loads(chat_history_json)
            print("loaded to python dictionary list: ", chat_history, type(chat_history))

    except ObjectDoesNotExist:
        return None, None

    if new_qa_pair:
        print("before extend: ", chat_history, type(chat_history))
        chat_history.extend(new_qa_pair)
        print("new_qa_pair: ", new_qa_pair, type(new_qa_pair))
        print("appended new chat: ", chat_history, type(chat_history))
        print("dumped and cached: ", json.dumps(chat_history, ensure_ascii=False),
              type(json.dumps(chat_history, ensure_ascii=False)))
        cache.set(chat_history_cache_key, json.dumps(chat_history, ensure_ascii=False), timeout=600)

    return ocr_texts, chat_history


class CustomJsonResponse(JsonResponse):
    def __init__(self, data, encoder=json.JSONEncoder, safe=True, json_dumps_params=None, **kwargs):
        if json_dumps_params is None:
            json_dumps_params = {}
        json_dumps_params["ensure_ascii"] = False
        super().__init__(data, encoder=encoder, safe=safe, json_dumps_params=json_dumps_params, **kwargs)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def enter_chatroom(request, chatroom_id):
    try:
        chatroom = ChatRoom.objects.get(pk=chatroom_id)
        if chatroom.entered:
            return JsonResponse({'error': 'cannot enter while entered'}, status=403)
        serializer = ChatRoomSerializer(chatroom)

        cache_chatroom_data(chatroom_id)

        chatroom.last_entered = timezone.now()
        chatroom.entered = True
        chatroom.leaved = False
        chatroom.save(update_fields=['last_entered'])

        return CustomJsonResponse(serializer.data, safe=False)
    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'ChatRoom not found'}, status=404)


def save_chat_history(chatroom_id, user_question, complete_answer):
    try:
        new_qa_pair = [{"role": 'user', "content": user_question}, {"role": 'assistant', "content": complete_answer}]
        cache_chatroom_data(chatroom_id, new_qa_pair)
    except ChatRoom.DoesNotExist:
        return JsonResponse({'error': 'ChatRoom not found'}, status=404)


@require_http_methods(["POST"])
@permission_classes([IsAuthenticated])
def create_stream(request, chatroom_id):
    try:
        decoded_body = request.body.decode('utf-8')
        data = json.loads(decoded_body)
        user_question = data.get('user_question', '')
        ocr_text_list, chat_history = cache_chatroom_data(chatroom_id)
        print("retrieved chat_history", chat_history, type(chat_history))

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    api_key = os.environ.get('OPEN_AI_API_KEY')
    client = OpenAI(api_key=api_key)
    system_feature = {
        "role": "system",
        "content": f"의료 검사지에 대한 상담을 진행한다.  반드시 한국말로, 의료 상담 관련 분야에 대해서만 간단히 말할 것.\
        또한 아래는 유저가 질의하고싶은 건강검사지의 검사내역이다 {ocr_text_list}\
        관련질문에 대해 검사내역과 대화 맥락에 기반해 성실히 답변해라"
    }

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


# @require_http_methods(["POST"])
# @permission_classes([IsAuthenticated])
# def create_stream(request, chatroom_id):
#     try:
#         decoded_body = request.body.decode('utf-8')
#         data = json.loads(decoded_body)
#         user_question = data.get('user_question', '')
#         ocr_text_list, chat_history = cache_chatroom_data(chatroom_id)
#         print("retrieved chat_history", chat_history, type(chat_history))
#
#     except json.JSONDecodeError:
#         return JsonResponse({'error': 'Invalid JSON'}, status=400)
#
#     api_key = os.environ.get('OPEN_AI_API_KEY')
#     client = OpenAI(api_key=api_key)
#     system_feature = {
#         "role": "system",
#         "content": f"의료 검사지에 대한 상담을 진행한다.  반드시 한국말로, 의료 상담 관련 분야에 대해서만 간단히 말할 것.\
#         또한 아래는 유저가 질의하고싶은 건강검사지의 검사내역이다 {ocr_text_list}\
#         관련질문에 대해 검사내역과 대화 맥락에 기반해 성실히 답변해라"
#     }
#
#     query = [system_feature]
#     if chat_history:
#         query.extend(chat_history)
#     query.append({"role": "user", "content": user_question})
#     print("final query:", query)
#     complete_answer = ""
#
#     def event_stream():
#         nonlocal complete_answer
#         for chunk in client.chat.completions.create(
#                 model="gpt-4-0613",
#                 messages=query,
#                 stream=True,
#         ):
#             chunk_message = chunk.choices[0].delta.content
#             state = chunk.choices[0].finish_reason
#             if state == 'stop':
#                 save_chat_history(chatroom_id, user_question, complete_answer)
#                 print("user_question:", user_question, "\ncomplete_answer", complete_answer)
#                 break
#             else:
#                 complete_answer += chunk_message
#             yield f"data: {chunk_message}\n\n"
#
#     response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
#     response['X-Accel-Buffering'] = 'no'
#     response['Cache-Control'] = 'no-cache'
#     return response
#
#
# @permission_classes([IsAuthenticated])
# def leave_chatroom(request, chatroom_id):
#     chat_history = cache.get(f"chatroom_{chatroom_id}_chat_history")
#     if chat_history:
#         chatroom = ChatRoom.objects.get(id=chatroom_id)
#         if chatroom.leaved:
#             return JsonResponse({"status": "cannot leave when already left"}, status=403)
#         chatroom.chat_history = json.loads(chat_history)
#         cache.delete(f"chatroom_{chatroom_id}_chat_history")
#         cache.delete(f"chatroom_{chatroom_id}_ocr_texts")
#         chatroom.leaved = True
#         chatroom.save()
#         return JsonResponse({"status": "success"})
# def save_chat_history(chatroom_id, user_question, complete_answer):
#     try:
#         new_qa_pair = [{"role": 'user', "content": user_question}, {"role": 'assistant', "content": complete_answer}]
#         cache_chatroom_data(chatroom_id, new_qa_pair)
#     except ChatRoom.DoesNotExist:
#         return JsonResponse({'error': 'ChatRoom not found'}, status=404)
