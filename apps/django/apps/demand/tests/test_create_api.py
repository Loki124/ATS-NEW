"""TODO-C: 建需求 API 端到端守护 (POST /api/v1/demands/)。

钉住 2026-08-11 修复的「建需求 500」链路, 防止回归:

  1. POST /demands/ 返回 201 (不再 500)。旧实现缺尾斜杠 + requested_by/hr/process
     必填缺 + code 留空撞 demands.code 唯一约束, 第二次创建即 500。
  2. 连建 ≥3 条需求, 每条 ``code`` 唯一 (D{yyyymmdd}{4位}) —— 直接守护"第二次
     创建即 500"的 code 唯一性 bug。
  3. ``process_version`` 非空且带 V 前缀 (与 RecruitmentProcess.current_version 对齐)。
  4. 恢复的 ``demand_type`` 字段能随请求往返 (SOCIAL 默认 / CAMPUS 显式写入)。

**全部用例自带 process + department + user seed**, 不依赖库内现状 (防"空跑必绿")。

响应约定: DemandViewSet 未覆写 create, 走 DRF 默认 → 出 camelCase 序列化体
(CamelCaseJSONRenderer), 无 {success,data} 外层包装。故 ``resp.json()`` 即对象本身。
"""
from __future__ import annotations

import pytest
from unittest.mock import patch
from rest_framework.test import APIClient

from apps.demand.models import Demand
from apps.demand.services import DemandCreateData, DemandService
from apps.process.models import RecruitmentProcess

LIST_URL = '/api/v1/demands/'


@pytest.fixture
def client(hr_user) -> APIClient:
    """已认证的 API client (HR 角色已获 recruit:demand:list, 见 fixtures_common 的
    session 级 role_permission seed)。"""
    api_client = APIClient()
    api_client.force_authenticate(user=hr_user)
    return api_client


@pytest.fixture
def process(db) -> RecruitmentProcess:
    """建需求 perform_create 默认取 is_latest=True & status=ENABLED 的流程。"""
    return RecruitmentProcess.objects.create(
        id='proc-todo-c',
        code='W_TODO_C',
        name='TODO-C 默认流程',
        current_version='V1.0',
        version_seq=1,
        is_latest=True,
        status='ENABLED',
        is_template=False,
        is_enabled=True,
    )


def _build_payload(department, **overrides) -> dict:
    payload = {
        'title': 'TODO-C 测试需求',
        'department': department.id,
        'headcount': 2,
    }
    payload.update(overrides)
    return payload


def _body(resp) -> dict:
    """兼容有无 {data} 包装: Demand 无包装, 取根; 若误带 data 也兼容。"""
    j = resp.json()
    return j.get('data', j)


def _latest_demand(department, title) -> Demand:
    """建需求响应体不含 id/code (DemandCreateSerializer 不输出), 落库后从 DB 取最新一条。"""
    return Demand.objects.filter(department=department, title=title).latest('created_at')


@pytest.mark.django_db
class TestCreateDemandAPI:
    def test_create_returns_201_not_500(self, client, department, process):
        """POST /demands/ → 201 (原 bug 是 500)。"""
        resp = client.post(LIST_URL, _build_payload(department), format='json')
        assert resp.status_code == 201, resp.content

        body = _body(resp)
        # DemandCreateSerializer 回显 demand_type (SOCIAL 默认)
        assert body['demandType'] == 'SOCIAL'

        demand = _latest_demand(department, 'TODO-C 测试需求')
        assert demand.process_id == process.id
        assert demand.process_version == 'V1.0'
        # 恢复的 demand_type 字段: 未传 → 默认 SOCIAL
        assert demand.demand_type == 'SOCIAL'

    def test_consecutive_creates_have_unique_codes(self, client, department, process):
        """连建 3 条, 每条 code 唯一 —— 守护"第二次创建即 500"的 code 唯一性 bug。"""
        codes = []
        for i in range(3):
            resp = client.post(
                LIST_URL, _build_payload(department, title=f'连建需求 {i}'),
                format='json',
            )
            assert resp.status_code == 201, resp.content
            codes.append(_latest_demand(department, f'连建需求 {i}').code)
        assert len(set(codes)) == 3, f'连建 code 必须唯一, 实际: {codes}'
        # 且都已落库
        assert Demand.objects.filter(code__in=codes).count() == 3

    def test_demand_type_round_trips(self, client, department, process):
        """恢复的 demand_type 字段能随请求往返: 显式 CAMPUS 落库并回显。"""
        resp = client.post(
            LIST_URL, _build_payload(department, demand_type='CAMPUS'),
            format='json',
        )
        assert resp.status_code == 201, resp.content
        body = _body(resp)
        assert body['demandType'] == 'CAMPUS'
        demand = _latest_demand(department, 'TODO-C 测试需求')
        assert demand.demand_type == 'CAMPUS'

    def test_create_delegates_to_demand_service(self, client, department, process, hr_user):
        """API 建需求必须走 DemandService.create_demand 单一来源 (TODO-A 收口),
        而非视图内联重写 —— 守护「分叉」不回流。

        用 patch.object(wraps=真实方法): 既真实落库, 又能断言被调用且入参正确。
        """
        with patch.object(
            DemandService, 'create_demand', wraps=DemandService.create_demand,
        ) as spy:
            resp = client.post(
                LIST_URL, _build_payload(department, demand_type='CAMPUS'),
                format='json',
            )
            assert resp.status_code == 201, resp.content
            spy.assert_called_once()
            call_data = spy.call_args.args[0]
            assert isinstance(call_data, DemandCreateData)
            assert call_data.process_id == process.id
            assert call_data.requested_by_id == hr_user.id
            assert call_data.hr_id == hr_user.id
            assert call_data.demand_type == 'CAMPUS'
