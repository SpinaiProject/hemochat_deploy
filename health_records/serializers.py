from rest_framework import serializers
from .models import *


class HealthRecordImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(allow_null=True, required=False)
    class Meta:
        model = HealthRecordImage
        fields = ['user', 'image', 'ocr_text', 'created_at']


# class HealthRecordFolderSerializer(serializers.ModelSerializer):
#     images = HealthRecordImageSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = HealthRecordFolder
#         fields = ['user','id', 'created_at', 'images']
