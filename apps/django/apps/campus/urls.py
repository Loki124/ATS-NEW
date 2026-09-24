"""校招专属功能路由（校园大使 + 宣讲会）。

挂在 /api/v1/campus-recruit/ 下（/api/v1/campus/ 已被 campus_control 占用）。

端点：
  GET    /ambassadors/              校园大使列表（按 recruit_type=campus 隔离）
  POST   /ambassadors/
  GET/PUT/DELETE /ambassadors/{id}/
  POST   /ambassadors/{id}/restore/ 恢复已软删大使
  GET/PUT /ambassadors/config/      模块启用开关配置（key=ambassador）

  GET    /sessions/                 宣讲会列表
  POST   /sessions/
  GET/PUT/DELETE /sessions/{id}/
  POST   /sessions/{id}/restore/    恢复已软删宣讲会
  GET/PUT /sessions/config/         模块启用开关配置（key=session）
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CampusAmbassadorViewSet,
    CampusModuleConfigView,
    CampusSessionViewSet,
)

router = DefaultRouter()
router.register(r'ambassadors', CampusAmbassadorViewSet, basename='campus-ambassador')
router.register(r'sessions', CampusSessionViewSet, basename='campus-session')

# 配置端点必须注册在 router 之前，避免被 ambassadors/<pk>/ 抢匹配（pk='config' → 404）。
urlpatterns = [
    path('ambassadors/config/', CampusModuleConfigView.as_view(), {'key': 'ambassador'}),
    path('sessions/config/', CampusModuleConfigView.as_view(), {'key': 'session'}),
]
urlpatterns += router.urls
