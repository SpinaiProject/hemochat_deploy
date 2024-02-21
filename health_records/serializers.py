from rest_framework import serializers
from .models import *


class HealthRecordImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = HealthRecordImage
        fields = ['user','id', 'image', 'ocr_text', 'created_at']


class HealthRecordFolderSerializer(serializers.ModelSerializer):
    images = HealthRecordImageSerializer(many=True, read_only=True)

    class Meta:
        model = HealthRecordFolder
        fields = ['user','id', 'created_at', 'images']
