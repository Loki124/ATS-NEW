"""信封回归测试 — 锁定 CandidateViewSet 的 create / retrieve / update 返回统一信封。

2026-09: CandidateViewSet 自定义 create (CandidateService 幂等查重) / update (PATCH),
外加大量 @action; 不能直接套 EnvelopeWriteMixin (会遮蔽自定义逻辑).
本批: EnvelopeReadOnlyMixin 接管 retrieve + 手动把 create/update 的 Response 包成
success_response, 保留全部自定义逻辑. 前端 getCandidate/updateCandidate 改为
data?.data ?? data 裸容错, 两种后端都兼容.

断言: create(201) / retrieve(200) / update(200) 均返回 {success: True, data: ...}.
"""
import random
import uuid


def _uniq_phone() -> str:
    """生成 11 位唯一纯数字手机号, 避开 CandidateService 幂等查重."""
    return f'139{random.randint(10 ** 7, 10 ** 8 - 1)}'


def test_candidate_envelope(auth_client):
    """CandidateViewSet: create / retrieve / update 必须信封化。"""
    name = f'信封测试候选人_{uuid.uuid4().hex[:8]}'

    # create (自定义 CandidateService.create_candidate, 现已返信封)
    resp = auth_client.post(
        '/api/v1/candidates/',
        data={'name': name, 'phone': _uniq_phone()},
        format='json',
    )
    assert resp.status_code == 201, resp.data
    assert resp.data['success'] is True, resp.data
    pk = resp.data['data']['id']

    # retrieve (EnvelopeReadOnlyMixin 接管默认 DRF retrieve)
    resp = auth_client.get(f'/api/v1/candidates/{pk}/')
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data

    # update (PATCH -> 自定义 update, 现已返信封)
    resp = auth_client.patch(
        f'/api/v1/candidates/{pk}/',
        data={'gender': '男'},
        format='json',
    )
    assert resp.status_code == 200
    assert resp.data['success'] is True, resp.data
