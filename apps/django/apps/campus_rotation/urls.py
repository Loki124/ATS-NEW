"""校招轮岗路由（挂在 /api/v1/campus-rotation/ 下）。

端点：
  GET/POST   /rotation-arrangements/              轮岗安排列表 / 新建
  GET/PUT/DELETE /rotation-arrangements/{id}/     详情 / 改 / 软删
  POST       /rotation-arrangements/{id}/restore/ 恢复软删
  POST       /rotation-arrangements/batch-assign/ 批量调整

  GET/POST   /live-rooms/                         直播间资源
  GET/PUT/DELETE /live-rooms/{id}/
  POST       /live-rooms/{id}/restore/

  GET/POST   /class-rooms/                         班级管理
  GET/PUT/DELETE /class-rooms/{id}/
  POST       /class-rooms/{id}/restore/

  GET/POST   /service-depts/                        客服部门资源（需求 4-3，S5-12）
  GET/PUT/DELETE /service-depts/{id}/
  POST       /service-depts/{id}/restore/

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
from rest_framework.routers import DefaultRouter

from django.urls import path

from .views import (
    ClassRoomViewSet,
    ConcurrentPostRecordViewSet,
    LiveRoomViewSet,
    ResourceBuSummaryView,
    RotationApprovalViewSet,
    RotationArrangementViewSet,
    RotationStageViewSet,
    ServiceDeptViewSet,
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
router.register(r'live-rooms', LiveRoomViewSet, basename='campus-live-room')
router.register(r'class-rooms', ClassRoomViewSet, basename='campus-class-room')
router.register(r'service-depts', ServiceDeptViewSet, basename='campus-service-dept')

urlpatterns = router.urls + [
    # 需求 4-1（S5-14）：轮岗资源 BU 三段式汇总
    path('resources/bu-summary/', ResourceBuSummaryView.as_view(), name='resource-bu-summary'),
]
