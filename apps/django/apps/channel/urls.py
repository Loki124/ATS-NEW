"""Channel URL Routes - /api/v1/channels/...

路由布局：
- /api/v1/channels/            ChannelViewSet        (渠道)
- /api/v1/channels/<pk>/       ChannelViewSet
- /api/v1/channels/costs/      ChannelCostViewSet    (渠道成本)
- /api/v1/channels/costs/<pk>/ ChannelCostViewSet

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现两个 ViewSet 都 register(r'')，
DefaultRouter 按注册顺序生成 URL，先注册的 ChannelCostViewSet 的
`^$` / `^(?P<pk>[^/.]+)/$` 把后注册的 ChannelViewSet 整块吃掉 → Channel 不可达。
修复要点：子资源必须用**独立前缀**且**先于** r'' 注册 —
若 `costs` 注册在 r'' 之后，`^(?P<pk>[^/.]+)/$` 会把 `costs/` 当成 pk 吞掉。
"""
from rest_framework.routers import DefaultRouter

from .views import ChannelCostViewSet, ChannelViewSet

router = DefaultRouter()
# 子资源前缀必须先注册：否则被 r'' 的 `^(?P<pk>[^/.]+)/$` 当 pk='costs' 吃掉
router.register(r'costs', ChannelCostViewSet, basename='channel-cost')
router.register(r'', ChannelViewSet, basename='channel')

urlpatterns = router.urls
