"""统一规则引擎 URL（Phase 1）—— 挂在 /api/v1/rule-engine/ 下，严格只读。"""
from django.urls import path

from .views import OperatorCatalogView, RuleListView, TriggerCatalogView

app_name = 'rule_engine'

urlpatterns = [
    path('rules/', RuleListView.as_view(), name='rule-list'),
    path('triggers/', TriggerCatalogView.as_view(), name='trigger-catalog'),
    path('operators/', OperatorCatalogView.as_view(), name='operator-catalog'),
]
