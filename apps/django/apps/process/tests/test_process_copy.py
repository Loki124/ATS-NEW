"""POST /processes/{id}/copy/ —— 复制为独立新流程（2026-10-16 新增端点）。

背景：FE ``recruitment-process.ts:copyProcess`` 一直打 ``POST /processes/{id}/copy/``，
而后端只有 ``clone-version``（同 code 追加版本），没有 ``copy`` → 流程详情页点「复制」必 404。

本文件锁定 copy 与 clone-version 的**语义边界**（新编号 / 不动源流程 / 不继承模板标记），
以及子配置深拷贝的完整性（阶段限时、流程内显示名等 2026-07-03 之后新增的字段也要带过去）。
"""
import uuid

PROCESS_LIST = '/api/v1/processes/'
STAGE_LIST = '/api/v1/stages/'
LINK_LIST = '/api/v1/process-stage-links/'

from apps.process.models import ProcessStageLink, RecruitmentProcess  # noqa: E402


def _uniq(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'


def _make_process_with_stage(auth_client, **extra):
    """建流程 + 1 个业务阶段并挂上 link，返回 (process_id, stage_id, link_id)。"""
    proc = auth_client.post(PROCESS_LIST, data={'name': _uniq('复制源流程')}, format='json')
    assert proc.status_code == 201, proc.data
    process_id = proc.data['data']['id']

    stage = auth_client.post(
        STAGE_LIST,
        data={'name': _uniq('复制源阶段'), 'stage_type': 'INTERVIEW'},
        format='json',
    )
    assert stage.status_code == 201, stage.data
    stage_id = stage.data['data']['id']

    payload = {'process_id': process_id, 'stage_id': stage_id, 'order': 1}
    payload.update(extra)
    link = auth_client.post(LINK_LIST, data=payload, format='json')
    assert link.status_code == 201, link.data
    return process_id, stage_id, link.data['data']['id']


def test_copy_creates_independent_process(auth_client):
    """复制产出**新编号**的新流程，且源流程完全不受影响。"""
    src_id, stage_id, _ = _make_process_with_stage(auth_client)

    # 先记下源流程的版本线快照，复制后逐项比对。
    # 注意：POST /processes/ 建流程时并不设置 is_latest（模型默认 False），
    # 所以这里断言的是「复制前后不变」，而不是「源一定是 latest」。
    before = RecruitmentProcess.objects.get(pk=src_id)
    snap = (before.code, before.version_seq, before.current_version, before.is_latest)

    resp = auth_client.post(f'{PROCESS_LIST}{src_id}/copy/', {}, format='json')
    assert resp.status_code == 201, resp.data
    assert resp.data['success'] is True, resp.data
    new_id = resp.data['data']['id']
    assert new_id != src_id, '副本必须是新行，不能是源行本身'

    src = RecruitmentProcess.objects.get(pk=src_id)
    new = RecruitmentProcess.objects.get(pk=new_id)
    assert new.code != src.code, f'副本应派生新 code，实得 {new.code} == {src.code}'
    assert new.version_seq == 1
    assert new.is_latest is True

    # 源流程的版本线一个字段都不能被动（clone 会改 is_latest，copy 不允许）
    src.refresh_from_db()
    assert (src.code, src.version_seq, src.current_version, src.is_latest) == snap, (
        '复制不该动源流程的版本线'
    )


def test_copy_carries_stage_config(auth_client):
    """阶段限时 / 流程内显示名 / 系统必含 这些字段必须一起复制过去。"""
    src_id, stage_id, _ = _make_process_with_stage(
        auth_client, stage_limit=72, custom_name='技术复试限时',
    )

    resp = auth_client.post(f'{PROCESS_LIST}{src_id}/copy/', {'new_name': '副本A'}, format='json')
    assert resp.status_code == 201, resp.data
    new_id = resp.data['data']['id']

    src_links = {
        l.stage_id: l for l in ProcessStageLink.objects.filter(process_id=src_id, deleted_at__isnull=True)
    }
    new_links = {
        l.stage_id: l for l in ProcessStageLink.objects.filter(process_id=new_id, deleted_at__isnull=True)
    }
    assert set(src_links) == set(new_links), '活跃阶段集合不一致'
    for sid, src_link in src_links.items():
        new_link = new_links[sid]
        assert new_link.stage_limit == src_link.stage_limit, f'{sid} 阶段限时没带过去'
        assert new_link.custom_name == src_link.custom_name, f'{sid} 流程内显示名没带过去'
        assert new_link.is_required == src_link.is_required
        assert new_link.order == src_link.order

    # FE onCopy 会读 data.name / data.id
    assert resp.data['data']['name'] == '副本A', resp.data['data']['name']


def test_copy_drops_template_flag(auth_client):
    """源是预置模板时，副本必须是普通流程（否则副本在列表里永久不可删）。"""
    src_id, _, _ = _make_process_with_stage(auth_client)
    RecruitmentProcess.objects.filter(pk=src_id).update(is_template=True, template_code='TPL_X')

    resp = auth_client.post(f'{PROCESS_LIST}{src_id}/copy/', {}, format='json')
    assert resp.status_code == 201, resp.data
    new = RecruitmentProcess.objects.get(pk=resp.data['data']['id'])
    assert new.is_template is False, '副本不应继承预置模板标记'
    assert new.template_code is None


def test_copy_skips_soft_deleted_links(auth_client):
    """软删 link 不进副本（软删行会永久占着 (process,stage) 唯一索引）。"""
    src_id, stage_id, link_id = _make_process_with_stage(auth_client)

    # 再加一个阶段，删掉它，制造一条软删 link
    stage2 = auth_client.post(
        STAGE_LIST, data={'name': _uniq('将被移除阶段'), 'stage_type': 'INTERVIEW'}, format='json',
    )
    assert stage2.status_code == 201, stage2.data
    link2 = auth_client.post(
        LINK_LIST,
        data={'process_id': src_id, 'stage_id': stage2.data['data']['id'], 'order': 2},
        format='json',
    )
    assert link2.status_code == 201, link2.data
    assert auth_client.delete(f'{LINK_LIST}{link2.data["data"]["id"]}/').status_code == 204

    resp = auth_client.post(f'{PROCESS_LIST}{src_id}/copy/', {}, format='json')
    assert resp.status_code == 201, resp.data
    new_id = resp.data['data']['id']

    assert ProcessStageLink.objects.filter(process_id=new_id, stage_id=stage_id).count() == 1
    assert ProcessStageLink._base_manager.filter(
        process_id=new_id, stage_id=stage2.data['data']['id'],
    ).count() == 0, '软删 link 不该被复制'


def test_copy_missing_process_returns_404(auth_client):
    assert auth_client.post(f'{PROCESS_LIST}not_exist_zzz/copy/', {}, format='json').status_code == 404
