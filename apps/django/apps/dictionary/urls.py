"""数据字典路由。"""
from rest_framework.routers import DefaultRouter

from .views import DictionaryItemViewSet, DictionaryTypeViewSet

router = DefaultRouter()
router.register(r'dictionary-types', DictionaryTypeViewSet, basename='dictionary-type')
router.register(r'dictionary-items', DictionaryItemViewSet, basename='dictionary-item')

urlpatterns = router.urls
