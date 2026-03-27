from django.urls import path
from .views import analyze, animate, task_status, chat

urlpatterns = [
    path('analyze', analyze),
    path('animate', animate),
    path('tasks/<str:task_id>', task_status),
    path('chat', chat),
]
