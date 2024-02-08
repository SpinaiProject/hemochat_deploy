from django.urls import path
from .views import *

urlpatterns = [
    path('create_assistant/', create_assistant_config, name='create_assistant_config'),
    path('create_thread/', create_thread, name='create_thread'),
    path('create_message/', create_message, name='create_message'),
    # path('create_run/', create_run, name='create_run'),
]
