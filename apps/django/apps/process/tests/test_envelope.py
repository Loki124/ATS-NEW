"""信封回归测试 — 锁定 4 个 process ViewSet 的写/详情端点返回统一信封。

2026-09: 给 RecruitmentStageViewSet / RecruitmentProcessViewSet / ProcessStageLinkViewSet
/ InterviewRoundViewSet 套 EnvelopeWriteMixin 后, 这些原本裸返 serializer.data 的端点
必须返回 {success: True, data: ...}, 否则前端 (recruitment-process.ts 用 r.data.data /
unwrap) 会拿到 undefined。

覆盖端点 (路径即 FE 实际调用路径, 见 config/urls.py api_v1_patterns):
- create (POST list)
- retrieve (GET detail) —— 由 mixin.retrieve 接管
- update (PATCH detail) —— DRF partial_update 委托给 mixin.update(partial=True)

权限: 用 auth_client (super_user, is_superuser) 过 HasProcessPermission 写校验
(HRBP_TIER = (SUPER_ADMIN, HRBP), user_has_any_role 对 is_superuser 短路放行)。
"""
import uuid

# FE 实际调用的 API 前缀 (config/urls.py: api/v1/ + 各 app 路由)
STAGE_LIST = '/api/v1/stages/'
PROCESS_LIST = '/api/v1/processes/'
LINK_LIST = '/api/v1/process-stage-links/'
ROUND_LIST = '/api/v1/recruitment-rounds/'


def _uniq(prefix: str) -> str:
    """生成带随机后缀的唯一名, 避免撞 RecruitmentStage 的 UNIQUE(name)。"""
    return f'{prefix}_{uuid.uuid4().hex[:8]}'


def test_recruitment_stage_envelope(auth_client):
    """RecruitmentStageViewSet: create / retrieve / update 必须信封化。"""
    # create
    resp = auth_client.post(
        STAGE_LIST,
        data={'name': _uniq('信封测试阶段'), 'stage_type': 'SCREEN'},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert resp.data['success'] is True, resp.data
    pk = resp.data['data']['id']

    # retrieve
    resp = auth_client.get(f'{STAGE_LIST}{pk}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data

    # update (PATCH -> partial_update 委托 mixin.update(partial=True))
    resp = auth_client.patch(
        f'{STAGE_LIST}{pk}/',
        data={'name': _uniq('信封测试阶段改')},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data


def test_recruitment_process_envelope(auth_client):
    """RecruitmentProcessViewSet: create(自定义已信封) / retrieve / update 必须信封化。"""
    # create (自定义 create 已返信封)
    resp = auth_client.post(
        PROCESS_LIST,
        data={'name': _uniq('信封测试流程')},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert resp.data['success'] is True, resp.data
    pk = resp.data['data']['id']

    # retrieve
    resp = auth_client.get(f'{PROCESS_LIST}{pk}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data

    # update (PATCH -> partial_update 委托 mixin.update)
    resp = auth_client.patch(
        f'{PROCESS_LIST}{pk}/',
        data={'name': _uniq('信封测试流程改')},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data


def test_process_stage_link_envelope(auth_client):
    """ProcessStageLinkViewSet: create / retrieve / update 必须信封化。"""
    # 准备: 一个流程 + 一个阶段 (流程 create 自动填起止 link, order 0/1)
    proc = auth_client.post(
        PROCESS_LIST,
        data={'name': _uniq('link流程')},
        format='json',
    )
    assert proc.status_code == 201, proc.data
    process_id = proc.data['data']['id']

    stage = auth_client.post(
        STAGE_LIST,
        data={'name': _uniq('link阶段'), 'stage_type': 'INTERVIEW'},
        format='json',
    )
    assert stage.status_code == 201, stage.data
    stage_id = stage.data['data']['id']

    # create: order=1 落在起止边界内 (start=0, end=1; 1<=1 允许)
    resp = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id, 'order': 1},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert resp.data['success'] is True, resp.data
    pk = resp.data['data']['id']

    # retrieve
    resp = auth_client.get(f'{LINK_LIST}{pk}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data

    # update
    resp = auth_client.patch(
        f'{LINK_LIST}{pk}/',
        data={'custom_name': '信封自定义名'},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data


def test_interview_round_envelope(auth_client):
    """InterviewRoundViewSet: create / retrieve / update 必须信封化。"""
    # create (auto R+三位)
    resp = auth_client.post(
        ROUND_LIST,
        data={'name': _uniq('信封测试轮次'), 'status': 'ACTIVE'},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert resp.data['success'] is True, resp.data
    pk = resp.data['data']['id']

    # retrieve
    resp = auth_client.get(f'{ROUND_LIST}{pk}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data

    # update
    resp = auth_client.patch(
        f'{ROUND_LIST}{pk}/',
        data={'name': _uniq('信封测试轮次改')},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data
