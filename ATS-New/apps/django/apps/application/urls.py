"""Application URL Routing"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ApplicationViewSet, GrabPoolViewSet, InvitationViewSet

router = DefaultRouter()
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'grab-pool', GrabPoolViewSet, basename='grab-pool')
router.register(r'invitations', InvitationViewSet, basename='invitation')

urlpatterns = [
    path('', include(router.urls)),
]
