"""8 处路由掩盖修复后的 **真实 HTTP** 可达性冒烟 (commit a78020a)

与 tests/test_route_mask_regression.py 的关系
============================================
``test_route_mask_regression.py`` 用 ``resolve()`` 锁死"URL 归属哪个 ViewSet"，
这防的是路由**再次**被掩盖。但它**不发请求** —— 而 ``GET /api/v1/applications/``
的 500 恰恰是 ``resolve()`` 能过、真实请求才炸（``AttributeError`` 发生在
序列化阶段）。两者是互补的两层：

    resolve() 层  →  URL 指向正确的 ViewSet
    HTTP 层 (本文件) → 该 ViewSet 真的能返回响应，而不是 500

⚠️ 本文件的局限（务必知悉）
==========================
这里是**空表**冒烟，只能抓住 import 错误、路由错挂、基类选错（如 GrabPoolViewSet
继承 ViewSet 导致 paginate_queryset AttributeError）这类"一请求就炸"的问题。
它**抓不到** SerializerMethodField 里的 bug —— 那类方法只在有行要序列化时才执行。
带数据的深度验证见 ``tests/test_application_grabpool_nonempty_regression.py``。

因此：新增子资源端点时，除了在这里登记 URL，还必须补一条**带数据**的用例。
"""
import pytest

# a78020a 打通的 8 处子资源 + 受影响的主资源
UNMASKED_LIST_ENDPOINTS = [
    '/api/v1/channels/costs/',           # ChannelCostViewSet
    '/api/v1/notifications/logs/',       # NotificationLogViewSet
    '/api/v1/automation-rules/logs/',    # AutomationLogViewSet
    '/api/v1/analytics/exports/',        # ExportTaskViewSet
    '/api/v1/integrations/sync-logs/',   # IntegrationSyncLogViewSet
    '/api/v1/talent-pool/tags/',         # TalentPoolTagViewSet
    '/api/v1/interviews/evaluations/',   # InterviewEvaluationViewSet
    '/api/v1/grab-pool/',                # GrabPoolViewSet.list (拆到顶层)
    '/api/v1/grab-pool/summary/',        # GrabPoolViewSet.summary
    '/api/v1/applications/',             # 被掩盖方的"加害者"，一并守住
]


@pytest.mark.django_db
@pytest.mark.parametrize('url', UNMASKED_LIST_ENDPOINTS)
def test_unmasked_endpoint_does_not_error(auth_client, url):
    """每个被打通的端点都必须真实返回 2xx —— 不能 404（路由又被吃）也不能 5xx。"""
    auth_client.raise_request_exception = False
    resp = auth_client.get(url)

    assert resp.status_code != 404, (
        f'{url} 返回 404 —— 路由可能再次被同 router 上的 r\'\' ViewSet 掩盖'
    )
    assert resp.status_code < 500, (
        f'{url} 返回 {resp.status_code}。响应: {resp.content[:600]}'
    )
    assert resp.status_code == 200, f'{url} 返回 {resp.status_code}，期望 200'
