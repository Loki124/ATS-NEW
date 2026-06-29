"""Field ACL URL Routes - /api/v1/field-acl/..."""
from rest_framework.routers import DefaultRouter

from .views import FieldACLViewSet

router = DefaultRouter()
router.register(r'', FieldACLViewSet, basename='field-acl')

urlpatterns = router.urls
