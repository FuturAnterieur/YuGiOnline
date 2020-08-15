

from django.urls import path

from . import views

app_name="socketio_app"
urlpatterns = [
    path('', views.index, name='index'),
    path('chat_space/', views.chat_space, name='chat_space'),
    path('new_duel/', views.create_new_duel, name='new_duel'),
    path('lobby/<int:duel_url>/', views.duel_lobby, name='duel_lobby'),
    path('enter_duel/<int:duel_url>/', views.enter_duel_room, name='enter_duel_room'),
    path('duel/<int:duel_url>/', views.duel_room, name='duel_room'),
]

