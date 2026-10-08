"""Reason Library 路由 — 17 个端点 (T01-T09 汇总).

挂载方式: config/urls.py 已 include('apps.reason_library.urls'),
前缀 /api/v1/reason-library/。
"""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .views.active_view import ActiveRuleView
from .views.rule_view import SceneRuleViewSet
from .views.scene_view import SceneView
from .views.tag_view import ReasonTagViewSet
from .views.wizard_view import WizardSaveView

router = DefaultRouter()
# 子资源前缀先注册: 'tags' / 'rules' / 'scenes' / 'active' 都优先于 r''
router.register(r'tags', ReasonTagViewSet, basename='reason-tag')
router.register(r'rules', SceneRuleViewSet, basename='scene-rule')

urlpatterns = router.urls + [
    # GET /scenes/  PUT /scenes/
    path('scenes/', SceneView.as_view(), name='reason-scenes'),
    # GET /active/?scene=xxx
    path('active/', ActiveRuleView.as_view(), name='reason-active'),
    # POST /rules/{id}/wizard/save/
    path('rules/<str:pk>/wizard/save/', WizardSaveView.as_view(), name='reason-wizard-save'),
]
