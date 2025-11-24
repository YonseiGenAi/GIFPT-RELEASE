from django.urls import path
from .views import analyze, task_status, chat

urlpatterns = [
    path('analyze', analyze),
    path('tasks/<str:task_id>', task_status),
    path('chat', chat),
]
