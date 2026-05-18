from apps.repositories.views import superusercreate
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AuthStatusView, LoginView, LogoutView, RegisterView, RepositoryViewSet

router = DefaultRouter()
router.register(r'repos', RepositoryViewSet, basename='repository')

urlpatterns = [

    path('auth/me/', AuthStatusView.as_view(), name='auth-me'),
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/logout/', LogoutView.as_view(), name='auth-logout'),
    path('', include(router.urls)),
    path("create-admin/", superusercreate.as_view(), name="create_prod_admin"),
]
