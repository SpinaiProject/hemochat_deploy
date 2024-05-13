from rest_framework import serializers
from .models import *
from health_records.serializers import HealthRecordImageSerializer


class ChatRoomListSerializer(serializers.ModelSerializer):
    representative_image = serializers.ImageField(source='health_records.first.image', read_only=True, allow_null=True)

    class Meta:
        model = ChatRoom
        fields = ['chatroom_id', 'title', 'updated_at', 'representative_image']

    def get_attribute(self, instance, attr):
        try:
            return super().get_attribute(instance, attr)
        except AttributeError:
            return None

class ChatRoomDetailSerializer(serializers.ModelSerializer):
    health_records = HealthRecordImageSerializer(many=True)

    class Meta:
        model = ChatRoom
        fields = '__all__'

# class ChatRoomSerializer(serializers.ModelSerializer):
#     recent_chat_history = serializers.SerializerMethodField()
#     summarized_chat_history = serializers.SerializerMethodField()
#     health_records = serializers.SerializerMethodField()
#
#     class Meta:
#         model = ChatRoom
#         fields = ['id', 'user', 'health_records', 'recent_chat_history', 'summarized_chat_history', 'last_entered',
#                   'entered', 'leaved']
#
#     def get_recent_chat_history(self, obj):
#         return obj.chat_history
#
#     def get_summarized_chat_history(self, obj):
#         return obj.summarized_chat_history
#
#     def get_health_records(self, obj):
#         health_records = obj.health_records.all()
#         serializer = HealthRecordImageSerializer(health_records, many=True)
#         return serializer.data
