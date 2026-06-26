"""StageRule URL 单独配置 - 兼容 root urls.py 引用

2026-06-17: 修复 — 之前 `from .urls import urlpatterns as process_urls` 拿到的是
            `urlpatterns = stage_urlpatterns`(./urls.py 末尾的兼容赋值),实际暴露的是
            RecruitmentStageViewSet,不是 StageRuleViewSet。改为显式从 .urls 导入
            正确的 rule_urlpatterns。
"""
from .urls import rule_urlpatterns

urlpatterns = rule_urlpatterns
