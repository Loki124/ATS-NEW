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
"""
from rest_framework.routers import DefaultRouter

from .views import (
    ClassRoomViewSet,
    LiveRoomViewSet,
    RotationArrangementViewSet,
)

router = DefaultRouter()
router.register(
    r'rotation-arrangements', RotationArrangementViewSet,
    basename='campus-rotation-arrangement',
)
router.register(r'live-rooms', LiveRoomViewSet, basename='campus-live-room')
router.register(r'class-rooms', ClassRoomViewSet, basename='campus-class-room')

urlpatterns = router.urls
