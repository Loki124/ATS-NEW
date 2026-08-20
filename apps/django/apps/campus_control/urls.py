"""校招管控路由。"""
from rest_framework.routers import DefaultRouter

from .views import RuleViewSet, PersonViewSet

router = DefaultRouter()
router.register(r'rules', RuleViewSet, basename='campus-rule')
router.register(r'persons', PersonViewSet, basename='campus-person')

urlpatterns = router.urls
