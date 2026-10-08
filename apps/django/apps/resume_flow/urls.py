"""Resume Flow URL Configs

URL 前缀：/resumes/approval-flows/
- GET    /               列表
- POST   /               新建
- GET    /{id}/          详情
- POST   /{id}/approve/  批准
- POST   /{id}/reject/   驳回
- POST   /{id}/delegate/ 转交
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ApprovalFlowViewSet

router = DefaultRouter()
router.register(r'', ApprovalFlowViewSet, basename='approval-flow')

urlpatterns = [
    path('', include(router.urls)),
]
