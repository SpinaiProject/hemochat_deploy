from django.urls import path
from .views import *

urlpatterns = [
    path('create_assistant/', create_assistant_config, name='create_assistant_config'),
    path('create_thread/', create_thread, name='create_thread'),
    path('create_message/', create_message, name='create_message'),
    # path('create_run/', create_run, name='create_run'),
    path('enter_chatroom/<uuid:chatroom_id>/', enter_chatroom, name='enter_chatroom'),
    path('create_chatroom/', create_chatroom, name='create_chatroom'),
    path('delete_chatroom/<uuid:chatroom_id>/', delete_chatroom, name='delete_chatroom'),
    path('create_stream/<uuid:chatroom_id>/', create_stream, name='create_stream'),
    path('leave_chatroom/<uuid:chatroom_id>/', leave_chatroom, name='leave_chatroom'),
]
