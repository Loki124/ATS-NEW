"""健康检查 URL"""
from django.urls import path
from .views_health import health_check

urlpatterns = [
    path('', health_check, name='health'),
]
