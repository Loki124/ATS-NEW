"""Talent Pool URL Routes - /api/v1/talent-pool/...

路由布局：
- /api/v1/talent-pool/                    TalentPoolEntryViewSet (人才库条目)
- /api/v1/talent-pool/<pk>/               TalentPoolEntryViewSet
- /api/v1/talent-pool/<pk>/activate/      TalentPoolEntryViewSet.activate
- /api/v1/talent-pool/<pk>/deactivate/    TalentPoolEntryViewSet.deactivate
- /api/v1/talent-pool/tags/               TalentPoolTagViewSet   (人才库标签)
- /api/v1/talent-pool/tags/<pk>/          TalentPoolTagViewSet

⚠️ 修复记录 (2026-08-06 寇豆码): 原实现两个 ViewSet 都 register(r'')，
TalentPoolTagViewSet 的 list/detail 路由被先注册的 Entry 吃掉 → 不可达。
子资源前缀 `tags` 必须先于 r'' 注册。
"""
from rest_framework.routers import DefaultRouter

from .views import TalentPoolEntryViewSet, TalentPoolTagViewSet

router = DefaultRouter()
# 子资源前缀必须先注册：否则被 r'' 的 `^(?P<pk>[^/.]+)/$` 当 pk='tags' 吃掉
router.register(r'tags', TalentPoolTagViewSet, basename='talent-pool-tag')
router.register(r'', TalentPoolEntryViewSet, basename='talent-pool-entry')

urlpatterns = router.urls
