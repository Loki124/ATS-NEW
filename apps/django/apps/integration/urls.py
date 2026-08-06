"""Integration URL Routes - /api/v1/integrations/...

路由布局：
- /api/v1/integrations/                 IntegrationConfigViewSet  (集成配置)
- /api/v1/integrations/<pk>/            IntegrationConfigViewSet
- /api/v1/integrations/<pk>/test/       IntegrationConfigViewSet.test
- /api/v1/integrations/sync-logs/       IntegrationSyncLogViewSet (同步日志, 只读)
- /api/v1/integrations/sync-logs/<pk>/  IntegrationSyncLogViewSet

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现两个 ViewSet 都 register(r'')，
IntegrationSyncLogViewSet 的 list/detail 路由被先注册的 Config 吃掉 → 不可达。
子资源前缀 `sync-logs` 必须先于 r'' 注册。
"""
from rest_framework.routers import DefaultRouter

from .views import IntegrationConfigViewSet, IntegrationSyncLogViewSet

router = DefaultRouter()
# 子资源前缀必须先注册：否则被 r'' 的 `^(?P<pk>[^/.]+)/$` 当 pk='sync-logs' 吃掉
router.register(r'sync-logs', IntegrationSyncLogViewSet, basename='integration-sync-log')
router.register(r'', IntegrationConfigViewSet, basename='integration-config')

urlpatterns = router.urls
