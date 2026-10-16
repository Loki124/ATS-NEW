"""流程-阶段关联「删了又加回来」回归（2026-10-15，ProcessDetailModal 保存链路）。

复刻兵哥控制台两条报错的真实链路：
  保存 #1 → 3b 软删被移除的 link（204）→ 3c 把同一阶段加回来 → POST 撞
      (process, stage) 唯一索引（该索引覆盖软删行）→ 1062 逃逸成 500（2026-10-15 前）。
  保存 #1 失败 → 前端 links 状态未刷新（3f 的 load() 只在成功路径跑）→
  保存 #2 → 3b 对已软删的 link 再发 DELETE → get_queryset 过滤 deleted_at → 404。

本文件先锁定「加回来」必须成功（复活软删行），再锁定「重复删除」必须幂等 204。
"""
import uuid

LINK_LIST = '/api/v1/process-stage-links/'
PROCESS_LIST = '/api/v1/processes/'
STAGE_LIST = '/api/v1/stages/'


def _uniq(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'


def _make_process_and_stage(auth_client):
    proc = auth_client.post(PROCESS_LIST, data={'name': _uniq('软删流程')}, format='json')
    assert proc.status_code == 201, proc.data
    process_id = proc.data['data']['id']

    stage = auth_client.post(
        STAGE_LIST,
        data={'name': _uniq('软删阶段'), 'stage_type': 'INTERVIEW'},
        format='json',
    )
    assert stage.status_code == 201, stage.data
    return process_id, stage.data['data']['id']


def _stage_count(auth_client, process_id: str) -> int:
    """列表接口里该流程的 stage_count（带 page_size 防翻页，且用检索断言而非 next() 兜底）。"""
    resp = auth_client.get(f'{PROCESS_LIST}?page_size=200')
    assert resp.status_code == 200, resp.data
    rows = resp.data['data'] if isinstance(resp.data['data'], list) else resp.data['data']['results']
    matched = [r for r in rows if r['id'] == process_id]
    assert len(matched) == 1, f'流程 {process_id} 不在列表首 200 条里（rows={len(rows)}）'
    return matched[0]['stage_count']


def test_readd_after_removal_is_allowed(auth_client):
    """移除阶段后再加回来（软删行仍占唯一组合）应当直接成功，而不是 400。"""
    process_id, stage_id = _make_process_and_stage(auth_client)

    created = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id, 'order': 1},
        format='json',
    )
    assert created.status_code == 201, created.data
    link_id = created.data['data']['id']

    # 3b：移除（软删）
    removed = auth_client.delete(f'{LINK_LIST}{link_id}/')
    assert removed.status_code == 204, removed.data

    # 3c：同一次编辑中又把它加回来 —— 这是用户真实操作，必须 201 且复用同一行
    readd = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id},
        format='json',
    )
    assert readd.status_code == 201, readd.data
    assert readd.data['success'] is True, readd.data
    # 复活的是同一行，不是新行（否则软删行会永久堆积占着唯一索引）
    assert readd.data['data']['id'] == link_id, readd.data


def test_delete_already_removed_link_is_idempotent(auth_client):
    """对已软删的 link 再发 DELETE（保存 #1 失败后未刷新的二次保存）应当幂等 204。"""
    process_id, stage_id = _make_process_and_stage(auth_client)

    created = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id, 'order': 1},
        format='json',
    )
    assert created.status_code == 201, created.data
    link_id = created.data['data']['id']

    assert auth_client.delete(f'{LINK_LIST}{link_id}/').status_code == 204
    # 二次保存：links 状态陈旧，再删一次
    again = auth_client.delete(f'{LINK_LIST}{link_id}/')
    assert again.status_code == 204, again.data


def test_add_duplicate_active_link_still_rejected(auth_client):
    """真重复添加（存在活跃行）仍须 400，不能因为支持复活而放行。"""
    process_id, stage_id = _make_process_and_stage(auth_client)

    first = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id, 'order': 1},
        format='json',
    )
    assert first.status_code == 201, first.data

    dup = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id},
        format='json',
    )
    assert dup.status_code == 400, dup.data
    # 序列化器字段级错误挂在信封的 errors 上（common/exceptions.py: errors=response.data）
    assert 'stage_id' in dup.data['errors'], dup.data


def test_stage_count_excludes_soft_deleted(auth_client):
    """列表/详情的 stage_count 只数活跃行（2026-10-16 兵哥截图：弹窗 10 / 列表 12）。

    ProcessStageLink 未把 SoftDeleteManager 设为默认 manager，obj.stage_links.count()
    会把「移除又加回来」留下的软删行也数进去，列表阶段数虚高。

    ⚠️ 基线必须动态取，不能写死「起止 2 + 业务 1 = 3」：本套件里存在
    django_db(transaction=True) 用例（如 apps/candidate），teardown 会 flush 整库，
    把迁移种子的全局起止阶段冲掉；pytest 又会把目录参数重排到单文件之前，
    于是「自动填充 2 条起止」这条前提在整跑时不成立（实测 count=1）。
    """
    process_id, stage_id = _make_process_and_stage(auth_client)

    # 创建流程后自动填充的起止 link 数（0/1/2 视库状态而定）
    base = _stage_count(auth_client, process_id)

    created = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id, 'order': 1},
        format='json',
    )
    assert created.status_code == 201, created.data
    link_id = created.data['data']['id']
    assert _stage_count(auth_client, process_id) == base + 1

    # 软删 1 条 → 回到基线（行还在，旧实现会得 base+1）
    assert auth_client.delete(f'{LINK_LIST}{link_id}/').status_code == 204
    assert _stage_count(auth_client, process_id) == base

    # 加回来（复活同一行）→ base+1，且没有新增行
    readd = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id},
        format='json',
    )
    assert readd.status_code == 201, readd.data
    assert _stage_count(auth_client, process_id) == base + 1

    # 详情端点继承同一个 get_stage_count，口径必须一致
    detail = auth_client.get(f'{PROCESS_LIST}{process_id}/')
    assert detail.status_code == 200, detail.data
    assert detail.data['data']['stage_count'] == base + 1, detail.data


def test_detail_stage_links_exclude_soft_deleted(auth_client):
    """详情接口的 stageLinks 也不能带软删行（实测 W001 返 8 条、活跃只有 2 条）。"""
    from apps.process.models import ProcessStageLink

    process_id, _ = _make_process_and_stage(auth_client)
    removed = auth_client.post(
        STAGE_LIST,
        data={'name': _uniq('详情软删阶段'), 'stage_type': 'INTERVIEW'},
        format='json',
    )
    assert removed.status_code == 201, removed.data
    gone = auth_client.post(
        LINK_LIST,
        # 不传 order：起止边界校验（BR-001）会拦越界顺序，前端同样省略该字段
        data={'process_id': process_id, 'stage_id': removed.data['data']['id']},
        format='json',
    )
    assert gone.status_code == 201, gone.data
    assert auth_client.delete(f'{LINK_LIST}{gone.data["data"]["id"]}/').status_code == 204

    # ⚠️ 基准必须用 _base_manager + 显式过滤：ProcessStageLink 的默认 manager **不过滤**
    #   软删（正是本次修的这一族问题），拿 objects 当「活跃」基准会把软删行算进去。
    all_rows = list(ProcessStageLink._base_manager.filter(process_id=process_id))
    soft_ids = {x.id for x in all_rows if x.deleted_at is not None}
    live_ids = {x.id for x in all_rows if x.deleted_at is None}
    assert soft_ids, '前置条件失败：本用例需要至少一条软删 link'

    detail = auth_client.get(f'{PROCESS_LIST}{process_id}/')
    assert detail.status_code == 200, detail.data
    returned = {l['id'] for l in detail.data['data']['stage_links']}
    assert returned == live_ids, (
        f'详情应恰好返回全部活跃 link：缺 {sorted(live_ids - returned)} / 多 {sorted(returned - live_ids)}'
    )
    assert not (returned & soft_ids), '软删 link 混进了详情 stageLinks'


def test_reference_count_ignores_soft_deleted(auth_client):
    """阶段配置「使用」列（reference_count）只数活跃 link + 未软删的启用流程。

    同 stage_count 一族的问题：反向关联 process_stage_links 会数进软删行，
    「流程里移除该阶段」留下的软删 link 让「使用」列虚高，且 is_referenced
    （删除/停用守卫 BR-002）会因此误拦。
    """
    from apps.process.models import RecruitmentProcess

    process_id, stage_id = _make_process_and_stage(auth_client)

    created = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id, 'order': 1},
        format='json',
    )
    assert created.status_code == 201, created.data
    link_id = created.data['data']['id']

    def _refs() -> int:
        resp = auth_client.get(f'{STAGE_LIST}?page_size=200')
        assert resp.status_code == 200, resp.data
        rows = resp.data['data'] if isinstance(resp.data['data'], list) else resp.data['data']['results']
        matched = [r for r in rows if r['id'] == stage_id]
        assert len(matched) == 1, f'阶段 {stage_id} 不在列表首 200 条里（rows={len(rows)}）'
        # 注意：APIClient 的 resp.data 是渲染前数据，键仍是 snake_case（camelCase 只在 JSON 渲染层）
        return matched[0]['reference_count']

    assert _refs() == 1

    # 软删 link → 不再算「被引用」（旧实现会得 1，删除/停用按钮被误置灰）
    assert auth_client.delete(f'{LINK_LIST}{link_id}/').status_code == 204
    assert _refs() == 0

    # 加回来（复活）→ 1；随后软删流程本身 → 0（软删流程不算「启用中流程」）
    readd = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id},
        format='json',
    )
    assert readd.status_code == 201, readd.data
    assert _refs() == 1

    RecruitmentProcess.objects.get(pk=process_id).soft_delete()
    assert _refs() == 0
