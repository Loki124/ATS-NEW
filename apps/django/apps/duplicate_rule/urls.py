from django.urls import path

from .views import (
    DuplicateCatalogView,
    DuplicateConfigView,
    DuplicateRuleDetailView,
    DuplicateRuleListView,
    DuplicateRuleResetView,
    DuplicateRuleToggleView,
)

urlpatterns = [
    # 查重项字段目录（强 / 中 / 弱）
    path('catalog/', DuplicateCatalogView.as_view()),
    # 重复候选人合并规则 + 重复申请管理（单例 JSON 配置）
    path('config/', DuplicateConfigView.as_view()),
    # 候选人查重规则
    path('rules/', DuplicateRuleListView.as_view()),
    # 注意：reset/ 必须早于 <int:pk>/ 之外无冲突（pk 为整数转换器），此处仍显式前置
    path('rules/reset/', DuplicateRuleResetView.as_view()),
    path('rules/<int:pk>/', DuplicateRuleDetailView.as_view()),
    path('rules/<int:pk>/toggle/', DuplicateRuleToggleView.as_view()),
]
