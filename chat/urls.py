"""
URL Configuration for Chat App
"""

from django.urls import path
from chat import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/messages/send', views.send_message, name='send_message'),
    path('api/messages/stream', views.stream_message, name='stream_message'),
    path('api/messages', views.get_messages, name='get_messages'),
    path('api/typing', views.get_typing_status, name='get_typing_status'),
    path('api/profile', views.get_user_profile, name='get_user_profile'),
    path('api/profile/username', views.set_username, name='set_username'),
    path('api/profile/onboard', views.onboard_user, name='onboard_user'),
    path('api/seed-protocols', views.seed_protocols, name='seed_protocols'),
    path('api/health', views.health_check, name='health_check'),
    # Voice endpoints
    path('api/voice/transcribe', views.transcribe_audio, name='transcribe_audio'),
    path('api/voice/speak', views.generate_speech, name='generate_speech'),
    path('api/voice/chat', views.voice_chat, name='voice_chat'),
]
