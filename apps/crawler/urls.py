from django.urls import path
from .views import trigger_crawler

urlpatterns = [
    path('trigger/', trigger_crawler, name='trigger_crawler'),
]
