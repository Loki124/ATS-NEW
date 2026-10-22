"""校招轮岗路由（挂在 /api/v1/campus-rotation/ 下）。

端点：
  GET/POST   /rotation-arrangements/              轮岗安排列表 / 新建
  GET/PUT/DELETE /rotation-arrangements/{id}/     详情 / 改 / 软删
  POST       /rotation-arrangements/{id}/restore/ 恢复软删
  POST       /rotation-arrangements/batch-assign/ 批量调整

  GET/POST   /resources/                           轮岗资源（直播间/客服部门/其他合一）
  GET/PUT/DELETE /resources/{id}/
  POST       /resources/{id}/restore/
  GET        /resources/export/                     导出 xlsx
  GET        /resources/template/                   下载导入模板 xlsx
  POST       /resources/import/                     批量导入 xlsx
  GET        /resources/bu-summary/                按 BU 分段汇总

  GET/POST   /class-rooms/                         班级管理
  GET/PUT/DELETE /class-rooms/{id}/
  POST       /class-rooms/{id}/restore/

  GET/POST   /rotation-stages/                      轮岗阶段（需求 5-8，S5-21）
  GET/PUT/DELETE /rotation-stages/{id}/

  GET/POST   /concurrent-post-records/              兼岗记录（需求 5-2，S5-25）
  GET/PUT/DELETE /concurrent-post-records/{id}/
  POST       /concurrent-post-records/{id}/sync/    摩卡同步（S5-26）

  GET/POST   /rotation-approvals/                   轮岗变更审批（需求 5-5，S5-17）
  GET/PUT/DELETE /rotation-approvals/{id}/
  POST       /rotation-approvals/{id}/approve/      审批通过（落字段）
  POST       /rotation-approvals/{id}/reject/       审批驳回（不落字段）
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ClassRoomViewSet,
    ConcurrentPostRecordViewSet,
    ResourceBuSummaryView,
    ResourceStatsOverviewView,
    RotationApprovalViewSet,
    RotationArrangementViewSet,
    RotationResourceViewSet,
    RotationStageViewSet,
)

router = DefaultRouter()
router.register(
    r'rotation-arrangements', RotationArrangementViewSet,
    basename='campus-rotation-arrangement',
)
router.register(
    r'rotation-stages', RotationStageViewSet,
    basename='campus-rotation-stage',
)
router.register(
    r'concurrent-post-records', ConcurrentPostRecordViewSet,
    basename='campus-concurrent-post-record',
)
router.register(
    r'rotation-approvals', RotationApprovalViewSet,
    basename='campus-rotation-approval',
)
# 2026-10-22 兵哥指令：直播间 + 客服部门整合为「轮岗资源」→
# 原 /live-rooms/ 与 /service-depts/ 两个端点合并为 /resources/（用 ?resource_type= 过滤）。
router.register(r'resources', RotationResourceViewSet, basename='campus-rotation-resource')
router.register(r'class-rooms', ClassRoomViewSet, basename='campus-class-room')

# ⚠️ 自定义路径必须排在 **router.urls 之前**：
#    DRF router 会生成 `resources/(?P<pk>[^/.]+)/` 的详情路由，而 pk 的正则
#    `[^/.]+` **能匹配 "bu-summary" / "stats-overview"** —— 一旦 router.urls 在前，
#    这两个自定义端点会被详情路由抢先命中 → 404（"No RotationResource matches..."）。
#    症状极具迷惑性：前端已 try/catch 并兜底到示例数据，页面看着完全正常，
#    但真实数据**从来没取到过**（`/resources/bu-summary/` 同样受害）。
#    → 约定：自定义子路径一律放在 router.urls 之前。
urlpatterns = [
    # 需求 4-1（S5-14）：轮岗资源 BU 分段汇总
    path('resources/bu-summary/', ResourceBuSummaryView.as_view(), name='resource-bu-summary'),
    # 需求 4-x：轮岗资源统计概览（BG × 当前BU 多维测算表）
    path(
        'resources/stats-overview/',
        ResourceStatsOverviewView.as_view(),
        name='resource-stats-overview',
    ),
] + router.urls
