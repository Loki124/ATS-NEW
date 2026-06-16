"""Process App URL Configs (统一)

URL 前缀：/api/v1/
- /stages/             阶段库
- /processes/          招聘流程
- /process-stage-links/ 流程-阶段关联
- /stage-rules/        阶段规则
- /process-templates/  流程模板
- /expressions/        表达式校验
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ExpressionValidationView,
    ProcessApplyTemplateView,
    ProcessStageLinkViewSet,
    ProcessTemplateViewSet,
    RecruitmentProcessViewSet,
    RecruitmentStageViewSet,
    StageRuleViewSet,
)

# ============================================================
# Routers
# ============================================================
stage_router = DefaultRouter()
stage_router.register(r'', RecruitmentStageViewSet, basename='stage')

process_router = DefaultRouter()
process_router.register(r'', RecruitmentProcessViewSet, basename='process')

link_router = DefaultRouter()
link_router.register(r'', ProcessStageLinkViewSet, basename='process-stage-link')

rule_router = DefaultRouter()
rule_router.register(r'', StageRuleViewSet, basename='stage-rule')

template_router = DefaultRouter()
template_router.register(r'', ProcessTemplateViewSet, basename='process-template')


# ============================================================
# 阶段库 URL (/api/v1/stages/...)
# ============================================================
stage_urlpatterns = [
    path('', include(stage_router.urls)),
]


# ============================================================
# 流程 URL (/api/v1/processes/...)
# ============================================================
process_urlpatterns = [
    # 自定义 actions 优先
    path('apply-template', ProcessApplyTemplateView.as_view(), name='process-apply-template'),
    path('', include(process_router.urls)),
]


# ============================================================
# 流程-阶段关联 URL (/api/v1/process-stage-links/...)
# ============================================================
link_urlpatterns = [
    path('', include(link_router.urls)),
]


# ============================================================
# 阶段规则 URL (/api/v1/stage-rules/...)
# ============================================================
rule_urlpatterns = [
    path('', include(rule_router.urls)),
]


# ============================================================
# 流程模板 URL (/api/v1/process-templates/...)
# ============================================================
template_urlpatterns = [
    path('', include(template_router.urls)),
]


# ============================================================
# 表达式校验 URL (/api/v1/expressions/...)
# ============================================================
expression_urlpatterns = [
    path('validate', ExpressionValidationView.as_view(), name='expression-validate'),
]


# ============================================================
# 兼容旧 url_* 引用 - 重新暴露具体 urlpatterns
# ============================================================
from django.urls import re_path

# 旧引用: urls_stage, urls_process, urls_link
urlpatterns = stage_urlpatterns
