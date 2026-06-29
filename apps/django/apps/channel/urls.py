"""Channel URL Routes - /api/v1/channels/..."""
from rest_framework.routers import DefaultRouter

from .views import ChannelCostViewSet, ChannelViewSet

router = DefaultRouter()
# costs 必须在 channel 之前注册（router 按顺序匹配）
router.register(r'costs', ChannelCostViewSet, basename='channel-cost')
router.register(r'', ChannelViewSet, basename='channel')

urlpatterns = router.urls
