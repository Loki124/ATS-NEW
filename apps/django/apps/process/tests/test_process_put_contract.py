"""PUT /api/v1/processes/{id}/ 契约回归（线上编辑流程 400 修复的钉子）。

线上 bug（2026-10，ats.lokisong.cloud）
=======================================
编辑招聘流程保存时报
``PUT /api/v1/processes/{id}/ 400 (Bad Request)``，双触发点：

- **触发点 A（必然触发）**：``RecruitmentProcessSerializer.Meta.fields`` 含
  **可写** ``status``，DRF 自动生成 ChoiceField 只认模型
  ``STATUS_CHOICES = [ENABLED, ARCHIVED]``（BR-106：流程无停用态，只能归档）；
  而 FE ``ProcessDetailModal.vue`` 发的是 ``status: 'ACTIVE' | 'INACTIVE'``
  （另一代 schema 的漂移）→ 400「"ACTIVE" 不是有效选项」。
  修复：``status`` 移入 ``read_only_fields``——状态变更只能走 ``archive``
  action / ``clone_version``，update 端点不再接受 status 写入。

- **触发点 B（配置了适用范围时触发）**：``validate_applicable_scope`` 只读
  ``value['items']`` 做 ``validate_syntax(expression, len(items))``；FE 发的
  却是 ``{mode, expression, indicators: [...]}``（``items`` 为另一代 schema）。
  有指标时 FE 自动生成非空表达式（如 "1 OR 2"）→ 后端 items=[] →
  编号越界 → 400「applicable_scope.expression 非法」。
  修复：``items = value.get('items') or value.get('indicators') or []``，
  兼容前端形态且不破坏旧 items 结构（权威结构见
  ``apps/django/seeds/03_social_tech_template.json``）。

本文件所有用例在修复前必须红（400），修复后必须绿；断言消息里带完整
response body，便于复现取证。
"""
from __future__ import annotations

import pytest

from apps.process.models import RecruitmentProcess

pytestmark = pytest.mark.django_db

# FE ProcessDetailModal.handleSave 更新路径的真实载荷（camelCase，
# 由 drf-camel-case parser 转 snake 后进 serializer）。
FRONTEND_UPDATE_PAYLOAD = {
    'name': 'PUT契约回归流程',
    'description': 'process put contract regression',
    'validateResumeScore': True,
    # 触发点 A: FE 旧 schema 的 ACTIVE/INACTIVE, 后端只认 ENABLED/ARCHIVED
    'status': 'ACTIVE',
    # is_enabled 是模型既有可写布尔字段 (models.py:211), FE 开关语义应对齐它
    'isEnabled': False,
    # 触发点 B: FE 发 indicators + 非空表达式, 后端旧代码只认 items
    'applicableScope': {
        'mode': 'ALL',
        'expression': '1 OR 2',
        'indicators': [
            {'key': 'department', 'mode': 'include', 'values': ['技术部']},
            {'key': 'level', 'mode': 'exclude', 'values': ['P7']},
        ],
    },
}


def make_process(code: str, name: str, **kwargs) -> RecruitmentProcess:
    defaults = dict(code=code, name=name, current_version='V1.0')
    defaults.update(kwargs)
    return RecruitmentProcess.objects.create(**defaults)


def put_process(client, process_id: str, payload: dict):
    """打 PUT /api/v1/processes/{id}/（FE 同款 camelCase JSON）。"""
    return client.put(
        f'/api/v1/processes/{process_id}/',
        data=payload,
        format='json',
    )


def body_of(resp) -> str:
    return resp.content.decode(errors='replace')


# ============================================================
# 1. 前端整包载荷：修复前必 400（触发点 A），修复后 200 且 is_enabled 落库
# ============================================================
def test_put_frontend_payload_succeeds_and_honors_is_enabled(auth_client) -> None:
    """FE 真实载荷（status='ACTIVE' + indicators  scope）必须 200。

    修复前：``"ACTIVE" is not a valid choice`` → 400（触发点 A 原文见断言消息）。
    修复后：200，``status`` 不被篡改（read_only），``is_enabled`` 按载荷落库。
    """
    process = make_process('W9001', 'PUT契约回归-整包')

    resp = put_process(auth_client, process.id, FRONTEND_UPDATE_PAYLOAD)

    assert resp.status_code == 200, (
        f'PUT 前端载荷应 200, 实得 {resp.status_code}: {body_of(resp)}'
        ' —— 触发点 A: status 可写 + FE 发 ACTIVE, 或触发点 B: indicators 不兼容'
    )
    process.refresh_from_db()
    # BR-106: update 端点不接受 status 写入, ENABLED 原值不动
    assert process.status == 'ENABLED', 'status 被 PUT 篡改了（应 read_only）'
    # is_enabled 保持可写, FE 开关值正确落库
    assert process.is_enabled is False, (
        f'is_enabled 未按载荷落库: {process.is_enabled} —— read_only 改错字段了？'
    )
    assert process.name == 'PUT契约回归流程'
    # 前端形态的 applicable_scope 原样持久化（JSONField 不改写结构）
    scope = process.applicable_scope
    assert scope.get('expression') == '1 OR 2'
    assert len(scope.get('indicators', [])) == 2


def test_put_status_is_read_only_even_with_valid_enum(auth_client) -> None:
    """status 对 update 端点整体 read_only：传合法值 'ARCHIVED' 也不生效。

    归档只能走 POST /processes/{id}/archive/（BR-106）。若把 status 加回
    可写字段，本用例立刻变红。
    """
    process = make_process('W9002', 'PUT契约回归-只读状态')

    resp = put_process(auth_client, process.id, {
        'name': process.name,
        'status': 'ARCHIVED',
    })

    assert resp.status_code == 200, f'应 200, 实得 {resp.status_code}: {body_of(resp)}'
    process.refresh_from_db()
    assert process.status == 'ENABLED', (
        'PUT 篡改了 status —— 状态变更只能走 archive action / clone_version'
    )


# ============================================================
# 2. 触发点 B 单测：indicators + 非空表达式
# ============================================================
def test_put_applicable_scope_with_indicators_and_expression(auth_client) -> None:
    """不带 status, 单独复现触发点 B：indicators + 非空表达式必须 200。

    修复前：``applicable_scope.expression 非法: 条件编号 1 超出范围`` → 400。
    """
    process = make_process('W9003', 'PUT契约回归-scope指标')

    resp = put_process(auth_client, process.id, {
        'name': process.name,
        'applicableScope': {
            'mode': 'ALL',
            'expression': '1 OR 2',
            'indicators': [
                {'key': 'department', 'mode': 'include', 'values': ['技术部']},
                {'key': 'position', 'mode': 'exclude', 'values': ['后端工程师']},
            ],
        },
    })

    assert resp.status_code == 200, (
        f'PUT indicators 形态 scope 应 200, 实得 {resp.status_code}: {body_of(resp)}'
        ' —— 触发点 B: validate_applicable_scope 不认 indicators'
    )
    process.refresh_from_db()
    assert process.applicable_scope['expression'] == '1 OR 2'


def test_put_applicable_scope_legacy_items_structure_still_valid(auth_client) -> None:
    """回归护栏：旧 items 结构（seeds/03_social_tech_template.json 权威形态）
    必须继续可用——兼容修复不得把旧结构打破。
    """
    process = make_process('W9004', 'PUT契约回归-scope旧结构')

    resp = put_process(auth_client, process.id, {
        'name': process.name,
        'applicableScope': {
            'items': [
                {'field': 'recruitment_type', 'op': 'eq', 'value': 'SOCIAL'},
                {'field': 'position_category', 'op': 'in', 'value': ['TECH']},
            ],
            'expression': '1 AND 2',
        },
    })

    assert resp.status_code == 200, f'旧 items 结构应 200, 实得 {resp.status_code}: {body_of(resp)}'
    process.refresh_from_db()
    assert len(process.applicable_scope['items']) == 2


def test_put_applicable_scope_invalid_expression_still_rejected(auth_client) -> None:
    """回归护栏：编号越界的表达式仍须 400——兼容修复不得把校验 neuter 掉。"""
    process = make_process('W9005', 'PUT契约回归-scope非法式')

    resp = put_process(auth_client, process.id, {
        'name': process.name,
        'applicableScope': {
            'mode': 'ALL',
            'expression': '1 AND 99',
            'indicators': [
                {'key': 'department', 'mode': 'include', 'values': ['技术部']},
            ],
        },
    })

    assert resp.status_code == 400, (
        f'越界表达式应 400, 实得 {resp.status_code}: {body_of(resp)}'
        ' —— validate_syntax 被绕过了？'
    )
    assert 'applicable_scope' in body_of(resp) or 'applicableScope' in body_of(resp)


def test_put_applicable_scope_null_expression_does_not_500(auth_client) -> None:
    """expression 显式为 null 时必须 200（不得 500）。

    2026-10-13 QA 独立复现实证：旧代码 ``value.get('expression', '')`` 在
    payload 显式发 ``expression: null`` 时取到 None（key 存在、值为 null），
    ``.strip()`` 抛 AttributeError → 500「服务器内部错误」。修复为
    ``(value.get('expression') or '')`` 后按空表达式跳过校验。
    """
    process = make_process('W9006', 'PUT契约回归-scope空表达式')

    resp = put_process(auth_client, process.id, {
        'name': process.name,
        'applicableScope': {
            'mode': 'ALL',
            'expression': None,
            'indicators': [
                {'key': 'department', 'mode': 'include', 'values': ['技术部']},
            ],
        },
    })

    assert resp.status_code == 200, (
        f'expression=null 应 200（按空表达式跳过校验）, 实得 {resp.status_code}: {body_of(resp)}'
        ' —— validate_applicable_scope 对 null expression 抛异常了？'
    )


# ============================================================
# 3. create 契约：is_enabled 落库（2026-10-13 补缺口）
# ============================================================
def post_process(client, payload: dict):
    """打 POST /api/v1/processes/（FE createProcess 同款 camelCase JSON）。"""
    return client.post('/api/v1/processes/', data=payload, format='json')


def test_create_process_honors_is_enabled_false(auth_client) -> None:
    """新建带 isEnabled=False 必须落库 is_enabled=False（不再是摆设）。

    修复前：``ProcessWithStagesCreateSerializer`` fields 不含 is_enabled 且
    create() 硬编码 is_enabled=True → FE 开关值被静默丢弃, 刷新后恒启用。
    """
    resp = post_process(auth_client, {
        'name': 'PUT契约回归-新建停用',
        'isEnabled': False,
    })

    assert resp.status_code == 201, f'应 201, 实得 {resp.status_code}: {body_of(resp)}'
    process = RecruitmentProcess.objects.get(name='PUT契约回归-新建停用')
    assert process.is_enabled is False, (
        f'is_enabled 未按载荷落库: {process.is_enabled} —— create 契约没接 is_enabled？'
    )
    # BR-106: status 仍恒 ENABLED（is_enabled 与 status 是两个维度）
    assert process.status == 'ENABLED'


def test_create_process_defaults_is_enabled_true(auth_client) -> None:
    """回归护栏：新建不传 isEnabled 时默认 True（字段 default 行为不变）。"""
    resp = post_process(auth_client, {'name': 'PUT契约回归-新建默认启用'})

    assert resp.status_code == 201, f'应 201, 实得 {resp.status_code}: {body_of(resp)}'
    process = RecruitmentProcess.objects.get(name='PUT契约回归-新建默认启用')
    assert process.is_enabled is True, '缺省 is_enabled 应为 True'
