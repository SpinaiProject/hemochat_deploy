from django.urls import path
from .views import *

urlpatterns = [
    path('create_health_records/', upload_images, name='upload_images'),
    path('list_user_health_records/', list_user_health_records, name='list_user_health_records'),
    path('delete_health_records/', delete_health_records, name='delete_health_records'),
    path('general_ocr_analysis/', general_ocr_analysis, name='general_ocr_analysis'),
]
