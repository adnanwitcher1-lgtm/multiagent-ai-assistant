# backend/api/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Auth endpoints
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/profile/', views.UserProfileView.as_view(), name='profile'),
    
    # Chat session endpoints
    path('sessions/', views.ChatSessionListView.as_view(), name='sessions'),
    path('sessions/<uuid:session_id>/', views.ChatSessionDetailView.as_view(), name='session-detail'),
    path('sessions/<uuid:session_id>/tasks/', views.SessionTasksView.as_view(), name='session-tasks'),
    
    # Task endpoints
    path('run/', views.RunTaskView.as_view(), name='run-task'),
    path('result/<uuid:task_id>/', views.TaskResultView.as_view(), name='task-result'),
    path('cancel/<uuid:task_id>/', views.CancelTaskView.as_view(), name='cancel-task'),
]