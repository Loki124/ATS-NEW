"""Interview Round URL Routes - /api/v1/recruitment-rounds

前端 recruitment-process.ts 调用路径（无尾斜杠）：
- GET    /api/v1/recruitment-rounds
- POST   /api/v1/recruitment-rounds
- PUT    /api/v1/recruitment-rounds/<id>
- PUT    /api/v1/recruitment-rounds/<id>/status

为了同时兼容带斜杠与不带斜杠的调用，这里不用 DefaultRouter，
显式注册 list/detail/status 三条路由及其斜杠别名。
"""
from django.urls import path

from .views import InterviewRoundViewSet

list_view = InterviewRoundViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

detail_view = InterviewRoundViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy',
})

status_view = InterviewRoundViewSet.as_view({
    'put': 'status',
})

urlpatterns = [
    path('recruitment-rounds', list_view, name='interview-round-list'),
    path('recruitment-rounds/', list_view, name='interview-round-list-slash'),
    path('recruitment-rounds/<str:pk>', detail_view, name='interview-round-detail'),
    path('recruitment-rounds/<str:pk>/', detail_view, name='interview-round-detail-slash'),
    path('recruitment-rounds/<str:pk>/status', status_view, name='interview-round-status'),
    path('recruitment-rounds/<str:pk>/status/', status_view, name='interview-round-status-slash'),
]
