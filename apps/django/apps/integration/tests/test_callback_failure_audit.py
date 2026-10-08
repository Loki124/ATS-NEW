"""P0 修复回归: 背调回调 apply_callback_to_order 抛异常时, 不得静默返回 200 SUCCESS.

锁定 apps/integration/views.py 中 BackgroundCheckCallbackView.post 第 5 步的新行为:
  - 验签通过(合法 payload)后, 若 apply_callback_to_order 内部失败:
      ① HTTP 状态码 == 500 (信封 code=50002), 绝不 200 SUCCESS
      ② 该 external_ref 对应的 IntegrationSyncLog.status == 'FAILED' 且 error_message 非空
      ③ 审计失败日志必须写回(便于供应商重试 + 运营排查)

测试用 bg_config fixture 提供 appId=sp_test / api_key=testkey 的合法 HMAC 配置,
helpers.make_payload 按 §5.2 同公式构造带合法签名的 payload; 仅通过 monkeypatch
让 apply_callback_to_order 抛异常, 验签与 SUCCESS 审计落库仍走真实逻辑.
"""
import pytest
from rest_framework.test import APIClient

from apps.integration import views
from apps.integration.models import IntegrationSyncLog
from apps.integration.tests.helpers import make_payload

CALLBACK_URL = '/api/v1/background-check/callback/'


def _forced_apply_failure(*args, **kwargs):
    """mock: 模拟订单状态机驱动(apply_callback_to_order)内部异常."""
    raise RuntimeError('forced apply_callback_to_order failure')


@pytest.mark.django_db
def test_callback_apply_failure_returns_500_and_audits_failed(bg_config, monkeypatch):
    # 仅让 apply 步骤失败; 验签 / SUCCESS 审计落库仍走真实逻辑.
    monkeypatch.setattr(views, 'apply_callback_to_order', _forced_apply_failure)

    number = 'FAIL-AUDIT-001'
    payload = make_payload(number, status=3, app_key='testkey')
    client = APIClient()
    resp = client.post(
        CALLBACK_URL,
        payload,
        format='json',
        HTTP_X_APP_ID='sp_test',
    )

    # ① 绝不静默 200 SUCCESS —— 必须 500
    assert resp.status_code == 500, resp.content
    body = resp.json()
    assert body.get('code') == 50002

    # ② 审计落库: 该 external_ref 的回调日志必须标记为 FAILED 且带错误信息
    log = IntegrationSyncLog.objects.get(
        config=bg_config, sync_type='CALLBACK', external_ref=number,
    )
    assert log.status == 'FAILED'
    assert log.error_message, 'FAILED 审计缺少 error_message'
    assert 'apply_callback_to_order' in log.error_message

    # ③ 明确: 信封绝不表示成功(响应体无 success=True)
    assert body.get('success') is not True
