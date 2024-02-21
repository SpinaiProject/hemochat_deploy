from rest_framework import serializers
from .models import ChatRoom
import json


class ChatRoomSerializer(serializers.ModelSerializer):
    recent_chat_history = serializers.SerializerMethodField()
    summarized_chat_history = serializers.SerializerMethodField()

    class Meta:
        model = ChatRoom
        fields = ['id', 'user', 'health_records', 'recent_chat_history', 'summarized_chat_history']

    def get_recent_chat_history(self, obj):
        return json.loads(obj.chat_history)

    def get_summarized_chat_history(self, obj):
        return json.loads(obj.summarized_chat_history)
