from rest_framework import serializers
from .models import *


class HealthRecordImageSerializer(serializers.ModelSerializer):
    image = serializers.ImageField(allow_null=True, required=False)
    class Meta:
        model = HealthRecordImage
        fields = ['id','user', 'title','image', 'ocr_text', 'created_at']

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            return request.build_absolute_uri(obj.image.url)
        return None

# class HealthRecordFolderSerializer(serializers.ModelSerializer):
#     images = HealthRecordImageSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = HealthRecordFolder
#         fields = ['user','id', 'created_at', 'images']
