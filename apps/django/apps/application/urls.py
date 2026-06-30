"""Application URL Routing"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, GrabPoolViewSet, InvitationViewSet

router = DefaultRouter()
router.register(r'', ApplicationViewSet, basename='application')
router.register(r'', GrabPoolViewSet, basename='grab-pool')
router.register(r'', InvitationViewSet, basename='invitation')

urlpatterns = [
    path('', include(router.urls)),
]
