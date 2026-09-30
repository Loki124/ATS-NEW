"""信封契约 — ExportTaskViewSet (信封收口 Batch 10, 后端-only).

ExportTaskViewSet 加 EnvelopeWriteMixin(首位基类) 覆盖 create / retrieve / update;
@action run_task/dashboard-summary 已手动信封, 保留.
注: create 序列化器未含 requested_by (DB 必填 FK, 后端未注入) → 当前 create 实际 500/未使用,
故本批不测 create 信封 (仅锁 list/retrieve/update 形状).

FE 影响面核查: 全仓 web/app/src 无 analytics/exports 端点 API 调用 → 零 FE 改动.

权限: IsHROrAbove, auth_client=super_user 经 is_super_admin 短路.
"""
import uuid

import pytest
from rest_framework.test import APIClient

from apps.analytics.models import ExportTask

pytestmark = pytest.mark.django_db

EXPORT_LIST = '/api/v1/analytics/exports/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


def _make_task(user) -> ExportTask:
    return ExportTask.objects.create(
        name='信封导出', entity='candidates',
        requested_by=user, format='XLSX', status='PENDING',
    )


def test_export_list_envelope(auth_client):
    resp = auth_client.get(EXPORT_LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)
    assert 'pagination' in resp.data


def test_export_retrieve_envelope(auth_client, super_user):
    task = _make_task(super_user)
    resp = auth_client.get(f'{EXPORT_LIST}{task.id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(task.id)
    assert resp.data['data']['name'] == '信封导出'


def test_export_update_envelope(auth_client, super_user):
    task = _make_task(super_user)
    resp = auth_client.patch(
        f'{EXPORT_LIST}{task.id}/', {'name': '信封导出改'}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.data['success'] is True
    assert resp.data['data']['name'] == '信封导出改'


# ============================================================
# DataSubscriptionViewSet (信封 initiative Batch G) — create 半信封补齐 code。
# FE api/data.ts: createSubscription 取 r.data.data, list 取 r.data.data (分页信封已含 code)。
# ============================================================
SUB_LIST = '/api/v1/data/subscriptions/'


def test_subscription_list_envelope(auth_client):
    resp = auth_client.get(SUB_LIST)
    # 空表也走分页信封 (StandardResultsSetPagination → success_response)
    assert resp.status_code == 200, resp.content
    assert resp.data['success'] is True
    assert resp.data['code'] == 0
    assert isinstance(resp.data['data'], list)


def test_subscription_create_envelope(auth_client):
    resp = auth_client.post(
        SUB_LIST,
        {'name': '信封订阅', 'resource': 'candidates', 'metric': 'all'},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    assert resp.data['success'] is True
    assert resp.data['code'] == 0            # 黄金标准: 缺 code 即半信封未收口
    assert resp.data['data']['name'] == '信封订阅'


def test_subscription_destroy_envelope(auth_client):
    """DataSubscriptionViewSet.destroy 软删, 现返 {success,data:None,code:0}."""
    from apps.analytics.models_data import DataSubscription
    sub = DataSubscription.objects.create(
        name='信封订阅-删', resource='candidates', metric='all',
    )
    resp = auth_client.delete(f'{SUB_LIST}{sub.id}/')
    assert resp.status_code == 200, resp.content
    assert resp.data['success'] is True
    assert resp.data['code'] == 0            # 黄金标准: 缺 code 即半信封未收口
    assert resp.data['data'] is None
    # 软删: 记录仍在库, 但 is_active 置 False, 从默认 (is_active=True) 查询集消失
    sub.refresh_from_db()
    assert sub.is_active is False
