from celery import shared_task
from celery.utils.log import get_task_logger
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

from .models import ChatRoom


# def get_active_chatrooms():
#     active_threshold = timezone.now() - timedelta(minutes=9)
#     active_chatrooms = ChatRoom.objects.filter(last_entered__gte=active_threshold).values_list('id', flat=True)
#     return list(active_chatrooms)

logger = get_task_logger(__name__)
@shared_task
def save_chat_history_to_db(chatroom_id, chat_history):
    logger.info(f"Starting to save chat history for chatroom {chatroom_id}...")
    chatroom = ChatRoom.objects.get(id=chatroom_id)
    chatroom.chat_history = chat_history
    # 요약 로직 추가
    chatroom.save()
    logger.info(f"Chat history for chatroom {chatroom_id} saved successfully.")


# @shared_task
# def save_chat_history_periodically():
#     for chatroom_id in get_active_chatrooms():
#         cache_key = f"chatroom_{chatroom_id}_chat_history"
#         chat_history = cache.get(cache_key)
#         if chat_history:
#             save_chat_history_to_db(chatroom_id, chat_history)
#     print("periodic save done.")
