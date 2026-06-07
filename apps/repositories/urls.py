from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthStatusView, LoginView, LogoutView, RegisterView, RepositoryViewSet, 
    ChatStartView, ChatMessageView
)

router = DefaultRouter()
router.register(r'repos', RepositoryViewSet, basename='repository')

urlpatterns = [

    path('auth/me/', AuthStatusView.as_view(), name='auth-me'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('chat/start/', ChatStartView.as_view(), name='chat-start'),
    path('chat/<uuid:session_id>/message/', ChatMessageView.as_view(), name='chat-message'),
    

    
    path('', include(router.urls)),
]
