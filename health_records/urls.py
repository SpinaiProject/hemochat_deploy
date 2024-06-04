from django.urls import path
from .views import *

urlpatterns = [
    path('create_health_records/', upload_images, name='upload_images'),
    path('user_health_records/', user_health_records, name='user_health_records'),
    #path('date_filtered_user_health_records/', date_filtered_user_health_records,
    #     name='date_filtered_user_health_records'),
    path('delete_health_records/', delete_health_records, name='delete_health_records'),
    path('general_ocr_analysis/', general_ocr_analysis, name='general_ocr_analysis'),
    # path('template_ocr_analysis/', template_ocr_analysis, name='template_ocr_analysis'),
    # path('template_ocr_analysis_for_gpt/', template_ocr_analysis_for_gpt, name='template_ocr_analysis_for_gpt'),
]
