"""Grab Pool URL Routes - /api/v1/grab-pool/... (挂载点见 config/urls.py)

路由布局（与 apps/application/views.py 模块 docstring 声明的契约一致）：
- GET  /api/v1/grab-pool/           GrabPoolViewSet.list      抢单池列表
- GET  /api/v1/grab-pool/summary/   GrabPoolViewSet.summary   抢单池汇总
- POST /api/v1/grab-pool/reassign/  GrabPoolViewSet.reassign  超时重分配（管理员）

⚠️ 修复记录 (2026-08-06 寇豆码): 原来 GrabPoolViewSet 与 ApplicationViewSet 在
apps/application/urls.py 里共用同一个 DefaultRouter 且都 register(r'')，
GrabPool 的 `^$` / `^summary/$` / `^reassign/$` 全被先注册的 ApplicationViewSet
的 `^$` 和 `^(?P<id>[^/.]+)/$` 吃掉 → 整个 ViewSet 不可达。
拆到独立 URLconf + 独立挂载点后互不干扰，且与 views.py 文档声明的
`/api/v1/grab-pool/` 契约对齐（放在 applications/ 之下会与
`/api/v1/applications/{id}/grab/` 语义混淆）。
"""
from rest_framework.routers import DefaultRouter

from .views import GrabPoolViewSet

router = DefaultRouter()
router.register(r'', GrabPoolViewSet, basename='grab-pool')

urlpatterns = router.urls
