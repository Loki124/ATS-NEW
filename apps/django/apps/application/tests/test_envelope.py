"""信封契约 — ApplicationViewSet (信封收口 Batch 9, 后端-only).

ApplicationViewSet 原 create 裸返 Response(ApplicationDetailSerializer(...).data, 201)
→ FE 若有消费方会取到 undefined(潜在 bug, 与 Position 同源). 本批:
  - 加 EnvelopeWriteMixin(首位基类) 覆盖 retrieve / update / partial_update;
  - 自定义 create 成功分支改 success_response 包裹(201), 错误分支(409/404)保留裸
    {'error':...} 与既有 @action 契约一致(change-process 端点断言 resp.json()['code']);
  - list 已信封(StandardResultsSetPagination), @action 无 FE 依赖保留裸响应;
  - 软删经 SoftDeleteViewSetMixin.perform_destroy, 不动.

FE 影响面核查 (前序已全仓 grep 确认): 全仓无 application.ts, application-form.ts 是
/standard-resume/application-form/ 另一资源, action 端点无 FE 调用 → 零 FE 改动.

权限: V2Permission + ScopeQuerysetMixin(recruit_type 默认 'social' 过滤, Application
默认 SOCIAL, 匹配; auth_client=super_user 经 is_super_admin 短路), 用 auth_client.

FSM: Application.state 是 FSMField(protected=True) → 禁 refresh_from_db, 断言均从响应信封取.
"""
import uuid

import pytest

from apps.application.models import Application
from apps.candidate.models import Candidate
from apps.position.models import Position, PositionState
from apps.process.models import (
    ProcessStageLink,
    RecruitmentProcess,
    RecruitmentStage,
    StageType,
)

pytestmark = pytest.mark.django_db

LIST = '/api/v1/applications/'


def _uid(prefix: str) -> str:
    return f'{prefix}-{uuid.uuid4().hex[:12]}'


def _make_process() -> tuple[RecruitmentProcess, RecruitmentStage, ProcessStageLink]:
    """造一条 ENABLED / is_latest 的流程 + 必经阶段, 供 create_application 解析首阶段."""
    process = RecruitmentProcess.objects.create(
        code=_uid('PROC'), name='信封流程', current_version='V1.0',
        version_seq=1, is_latest=True, status='ENABLED',
    )
    stage = RecruitmentStage.objects.create(
        code=_uid('STG'), name='信封阶段', stage_type=StageType.SCREEN,
    )
    link = ProcessStageLink.objects.create(
        process=process, stage=stage, order=1, is_required=True,
    )
    return process, stage, link


@pytest.fixture
def scenario(db, department, super_user):
    process, stage, link = _make_process()
    position = Position.objects.create(
        code=f'P{uuid.uuid4().hex[:8].upper()}',
        title='信封职位', department=department,
        hiring_manager=super_user, owner=super_user,
        process=process, state=PositionState.DRAFT,
    )
    candidate = Candidate.objects.create(name='信封候选人', phone='13900000001')
    return {
        'user': super_user, 'process': process, 'stage': stage, 'link': link,
        'position': position, 'candidate': candidate,
    }


def _make_application(scenario: dict) -> Application:
    """直接建申请 (state 走默认 PENDING, 避开 FSM 受保护赋值)."""
    return Application.objects.create(
        code=_uid('APP'),
        candidate=scenario['candidate'],
        position=scenario['position'],
        process=scenario['process'],
        workflow_version=scenario['process'].current_version,
        current_link=scenario['link'],
        current_stage=scenario['stage'],
    )


def test_application_retrieve_envelope(auth_client, scenario):
    app = _make_application(scenario)
    resp = auth_client.get(f'{LIST}{app.id}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert resp.data['data']['id'] == str(app.id)


def test_application_update_envelope(auth_client, scenario):
    # PATCH total_time_limit_days 走 EnvelopeWriteMixin.update → success_response → 信封.
    app = _make_application(scenario)
    resp = auth_client.patch(
        f'{LIST}{app.id}/', {'total_time_limit_days': 7}, format='json')
    assert resp.status_code == 200, resp.content
    assert resp.data['success'] is True
    # state 是 protected FSMField, 禁 refresh_from_db; 从响应信封断言.
    assert resp.data['data']['total_time_limit_days'] == 7


def test_application_list_envelope(auth_client, scenario):
    _make_application(scenario)
    resp = auth_client.get(LIST)
    assert resp.status_code == 200
    assert resp.data['success'] is True
    assert isinstance(resp.data['data'], list)
    assert 'pagination' in resp.data


def test_application_create_envelope(auth_client, scenario):
    # 验证修复: 后端 create 现返回 {success,data}, 与 Position 同源的潜在 null bug 一并根治.
    before = Application.objects.count()
    resp = auth_client.post(LIST, {
        'candidate_id': str(scenario['candidate'].id),
        'position_id': str(scenario['position'].id),
    }, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.data['success'] is True
    # 关键: data 内含 id 与自动生成的 code, 否则 FE 取不到.
    assert 'id' in resp.data['data']
    assert resp.data['data']['code']  # 非空, _gen_application_code
    assert resp.data['data']['state'] == 'PENDING'
    assert Application.objects.count() == before + 1


def test_application_create_error_branch_stays_raw(auth_client, scenario):
    # 错误分支(404 缺职位)保持裸 {'error','code'}, 与既有 @action 契约一致.
    resp = auth_client.post(LIST, {
        'candidate_id': str(scenario['candidate'].id),
        'position_id': 'no-such-position-id',
    }, format='json')
    assert resp.status_code == 404, resp.content
    assert 'error' in resp.data
    assert resp.data.get('code') == 'NOT_FOUND'
    # 错误体不应带 success 信封字段(保持裸, 与 change-process 409 断言同款).
    assert 'success' not in resp.data
