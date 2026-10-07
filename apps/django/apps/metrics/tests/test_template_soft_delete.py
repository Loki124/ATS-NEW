"""LIFE-1 P2：指标模板软删 + 真撤销（restore）端点测试。

覆盖：
    - 软删后默认 manager 过滤：列表不含、retrieve 404、all_objects 仍可取（行在、id 不变）。
    - restore 端点：列表重新包含、id 不变、retrieve 200、deleted_at 清空、updated_by 记录。
    - 规则 conditions 存该模板 id 字符串，软删 + restore 后模板行仍在、id 不变 → 引用有效。
    - 软删被规则引用的模板也成功（D1：destroy 不再 400 拦截）。
"""
from __future__ import annotations

import pytest

from apps.metrics.models import (
    AtomicMetric,
    MetricDataType,
    MetricRule,
    MetricTemplate,
)

pytestmark = pytest.mark.django_db

BASE = '/api/v1/metrics/'


def _make_template(name: str = 'P2 软删模板') -> MetricTemplate:
    """ORM 直接建模板（绕过序列化校验，聚焦软删/restore 行为）。"""
    am = AtomicMetric.objects.create(
        name='P2 原子指标', source_path='candidate.age',
        data_type=MetricDataType.NUMBER, status='enabled',
    )
    return MetricTemplate.objects.create(
        name=name, atomic_metric=am, operators=['GT'], status='enabled',
    )


def _unwrap(resp):
    body = resp.data
    if isinstance(body, dict) and 'success' in body and 'data' in body:
        return body['data']
    return body


def _list_ids(resp) -> set:
    data = _unwrap(resp)
    results = data['results'] if isinstance(data, dict) and 'results' in data else data
    return {t['id'] for t in results}


def test_soft_delete_excluded_from_default_manager(super_user):
    """软删后：objects（默认 manager）查不到，all_objects 仍可取且 deleted_at 已置、id 不变。"""
    tpl = _make_template()
    tpl.soft_delete()  # 仅置 deleted_at
    assert not MetricTemplate.objects.filter(id=tpl.id).exists()
    row = MetricTemplate.all_objects.get(id=tpl.id)
    assert row.deleted_at is not None
    assert row.id == tpl.id


def test_destroy_api_soft_deletes_and_hides(auth_client, super_user):
    """DELETE 端点软删：204；列表不含；retrieve 404；all_objects 仍可取且 updated_by 记录。"""
    tpl = _make_template()
    resp = auth_client.delete(f'{BASE}templates/{tpl.id}/')
    assert resp.status_code == 204
    # 列表不含
    assert tpl.id not in _list_ids(auth_client.get(f'{BASE}templates/'))
    # retrieve 404
    assert auth_client.get(f'{BASE}templates/{tpl.id}/').status_code == 404
    # all_objects 仍可取（软删非硬删）
    row = MetricTemplate.all_objects.get(id=tpl.id)
    assert row.deleted_at is not None
    assert row.updated_by_id == super_user.id


def test_restore_action_brings_back_same_id(auth_client, super_user):
    """POST restore：200；列表重新包含；id 不变；retrieve 200；deleted_at 清空且 updated_by 记录。"""
    tpl = _make_template()
    auth_client.delete(f'{BASE}templates/{tpl.id}/')
    resp = auth_client.post(f'{BASE}templates/{tpl.id}/restore/')
    assert resp.status_code == 200
    body = _unwrap(resp)
    assert body['id'] == tpl.id
    # 列表重新包含
    assert tpl.id in _list_ids(auth_client.get(f'{BASE}templates/'))
    # retrieve 200
    assert auth_client.get(f'{BASE}templates/{tpl.id}/').status_code == 200
    # deleted_at 清空 + updated_by 记录
    row = MetricTemplate.all_objects.get(id=tpl.id)
    assert row.deleted_at is None
    assert row.updated_by_id == super_user.id


def test_soft_delete_preserves_rule_reference(auth_client):
    """规则 conditions 存该模板 id；软删 + restore 后模板行仍在、id 不变 → 引用有效。"""
    tpl = _make_template()
    rule = MetricRule.objects.create(
        name='P2 引用规则', scene='FILTER', action_type='DEDUCT',
        conditions=[{'templateId': str(tpl.id), 'operator': 'GT', 'value': '30'}],
    )
    # 软删
    auth_client.delete(f'{BASE}templates/{tpl.id}/')
    row = MetricTemplate.all_objects.get(id=tpl.id)
    assert row.deleted_at is not None
    assert row.id == tpl.id
    # restore 后引用仍有效（规则 conditions 里的 templateId 仍是原 id）
    auth_client.post(f'{BASE}templates/{tpl.id}/restore/')
    rule.refresh_from_db()
    assert rule.conditions[0]['templateId'] == str(tpl.id)


def test_destroy_referenced_template_succeeds_no_400(auth_client):
    """D1：软删被规则引用的模板也成功（destroy 不再 400 拦截），且为软删（行仍在）。"""
    tpl = _make_template()
    MetricRule.objects.create(
        name='P2 引用规则2', scene='TALENT_POOL', action_type='VETO',
        conditions=[{'templateId': str(tpl.id), 'operator': 'GT', 'value': '30'}],
    )
    resp = auth_client.delete(f'{BASE}templates/{tpl.id}/')
    assert resp.status_code == 204
    # 软删（非硬删）：行仍在
    assert MetricTemplate.all_objects.filter(id=tpl.id).exists()
