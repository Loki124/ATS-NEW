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
    """
    process_id, stage_id = _make_process_and_stage(auth_client)

    created = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id, 'order': 1},
        format='json',
    )
    assert created.status_code == 201, created.data
    link_id = created.data['data']['id']

    # 创建流程时自动填充起止 2 条 + 本阶段 1 条 = 3
    def _count(resp):
        assert resp.status_code == 200, resp.data
        rows = resp.data['data'] if isinstance(resp.data['data'], list) else resp.data['data']['results']
        row = next(r for r in rows if r['id'] == process_id)
        return row['stage_count']

    assert _count(auth_client.get(PROCESS_LIST)) == 3

    # 软删 1 条 → 2；行还在（共 3 行），旧实现会数成 3
    assert auth_client.delete(f'{LINK_LIST}{link_id}/').status_code == 204
    assert _count(auth_client.get(PROCESS_LIST)) == 2

    # 加回来（复活同一行）→ 回到 3，且没有新增行
    readd = auth_client.post(
        LINK_LIST,
        data={'process_id': process_id, 'stage_id': stage_id},
        format='json',
    )
    assert readd.status_code == 201, readd.data
    assert _count(auth_client.get(PROCESS_LIST)) == 3

    # 详情端点继承同一个 get_stage_count，口径必须一致
    detail = auth_client.get(f'{PROCESS_LIST}{process_id}/')
    assert detail.status_code == 200, detail.data
    assert detail.data['data']['stage_count'] == 3, detail.data
