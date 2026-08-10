"""T5 回归：``list_process_versions`` 与 ``archive_process``（V7 / V8 / V9 / X3 + 产品 Q5）。

四个被修的缺陷
==============
- **V9-排序**：``order_by('current_version')`` 是**字典序**。实测
  ``['V1.0', 'V1.10', 'V1.2', 'V10.0', 'V2.0']``——第 10 版排在第 2 版前面。
  → :func:`test_versions_are_ordered_by_integer_seq_not_lexicographically`
- **V9-N+1**：推导式里逐行读 ``p.reference_count`` 属性，N 行发 1+N 条 COUNT。
  → :func:`test_list_versions_is_constant_query_count`
- **V8/X3-软删口径**：版本列表不过滤软删行；``RecruitmentProcess.reference_count``
  也不过滤软删 Demand，而同语义的 ``is_process_referenced()`` 却过滤——同一个问题
  两套口径，删除校验和提示文案会互相打脸。
  → :func:`test_soft_deleted_version_row_disappears_from_list`
  → :func:`test_reference_count_ignores_soft_deleted_demands`
- **V7-返回值形状**：``archive_process`` 早退分支返回 ``reference_count`` 为 **bool**
  （``is_process_referenced()`` 的返回值）且缺 ``archived_at`` 键，调用方按 int 用会
  静默拿到 ``True``/``False``。
  → :func:`test_archive_returns_identical_shape_on_both_branches`

以及产品 Q5：**归档作用于整条 code 线**，不是单个版本行。只归档 ``is_latest`` 那行会
造出「列表页显示已归档、``list_process_versions`` 里历史版本仍 ENABLED」这种无法向
用户解释的状态。→ :func:`test_archive_covers_whole_code_line`
"""
from __future__ import annotations

import pytest

from apps.common.exceptions import StateTransitionError
from apps.process.models import RecruitmentProcess
from apps.process.services.versioning import archive_process, list_process_versions

pytestmark = pytest.mark.django_db


def make_process(code: str, seq: int, *, is_latest: bool = False, **kwargs) -> RecruitmentProcess:
    defaults = dict(
        code=code,
        name=f'{code} 流程 V{seq}',
        current_version=f'V{seq}.0',
        version_seq=seq,
        is_latest=is_latest,
    )
    defaults.update(kwargs)
    return RecruitmentProcess.objects.create(**defaults)


def make_demand(process, department, user, code: str):
    from apps.demand.models import Demand

    return Demand.objects.create(
        code=code, title=f'{code} 需求', department=department,
        requested_by=user, hr=user, headcount=1,
        process=process, process_version=process.current_version,
    )


# ============================================================
# 1. list_process_versions
# ============================================================
def test_versions_are_ordered_by_integer_seq_not_lexicographically() -> None:
    """**V9 钉子**：seq 1/2/10 必须排成 [1, 2, 10]，而不是字典序的 [1, 10, 2]。

    把服务里的 ``order_by('version_seq')`` 改回 ``order_by('current_version')``，
    本用例立刻变红。
    """
    make_process('W960', 1)
    make_process('W960', 2)
    make_process('W960', 10, is_latest=True)

    rows = list_process_versions('W960')

    assert [r['version_seq'] for r in rows] == [1, 2, 10], (
        f'按 current_version 字典序排了：{[r["version"] for r in rows]}'
        ' —— 版本号的权威来源是整数 version_seq'
    )
    assert [r['version'] for r in rows] == ['V1.0', 'V2.0', 'V10.0']


def test_soft_deleted_version_row_disappears_from_list() -> None:
    """**V8 钉子**：软删的版本行不得出现在版本列表里。"""
    make_process('W961', 1, is_latest=True)
    doomed = make_process('W961', 2)
    doomed.soft_delete()

    rows = list_process_versions('W961')

    assert [r['version_seq'] for r in rows] == [1], '软删行仍在版本列表里'


def test_list_versions_exposes_seq_and_latest_with_exactly_one_latest() -> None:
    """返回体必须带 ``version_seq`` / ``is_latest``，且恰有一条 ``is_latest=True``。"""
    make_process('W962', 1)
    make_process('W962', 2)
    latest = make_process('W962', 3, is_latest=True)

    rows = list_process_versions('W962')

    expected_keys = {
        'id', 'version', 'version_seq', 'is_latest',
        'name', 'status', 'created_at', 'reference_count',
    }
    assert all(set(r) == expected_keys for r in rows)
    flagged = [r['id'] for r in rows if r['is_latest']]
    assert flagged == [latest.id], (
        f'is_latest=True 的行有 {len(flagged)} 条（应恰好 1 条，由 C3\' 兜底）'
    )


def test_list_versions_is_constant_query_count(django_assert_num_queries) -> None:
    """**N+1 钉子**：无论多少行，查询数恒为 1。

    老实现是 1（列表）+ N（每行一次 ``reference_count`` COUNT）。用 6 行做样本——
    只要退回属性读法，这里就会变成 7 条而变红。
    """
    for seq in range(1, 7):
        make_process('W963', seq, is_latest=(seq == 6))

    with django_assert_num_queries(1):
        rows = list_process_versions('W963')
        assert len(rows) == 6


def test_list_versions_counts_only_live_demands(department, hr_user) -> None:
    """``reference_count`` 只数 live Demand，与 ``is_process_referenced`` 口径一致。"""
    process = make_process('W964', 1, is_latest=True)
    make_demand(process, department, hr_user, 'D-T5-001')
    make_demand(process, department, hr_user, 'D-T5-002').soft_delete()

    rows = list_process_versions('W964')

    assert rows[0]['reference_count'] == 1, '软删的 Demand 被算进了引用数'
    assert type(rows[0]['reference_count']) is int


def test_list_versions_returns_empty_for_unknown_or_fully_deleted_code() -> None:
    """code 不存在、或整条线都被软删 → 返回 ``[]``，不抛异常。"""
    assert list_process_versions('W-NOPE') == []

    row = make_process('W965', 1, is_latest=True)
    row.soft_delete()
    assert list_process_versions('W965') == []


# ============================================================
# 2. reference_count 属性（X3）
# ============================================================
def test_reference_count_ignores_soft_deleted_demands(department, hr_user) -> None:
    """**X3 钉子**：模型属性与 ``is_process_referenced()`` 必须同一口径。"""
    from apps.process.services.versioning import is_process_referenced

    process = make_process('W966', 1, is_latest=True)
    make_demand(process, department, hr_user, 'D-T5-003').soft_delete()

    assert process.reference_count == 0, 'reference_count 把软删 Demand 也算进去了'
    assert is_process_referenced(process) is False
    assert type(process.reference_count) is int


# ============================================================
# 3. archive_process（V7 + 产品 Q5）
# ============================================================
def test_archive_covers_whole_code_line() -> None:
    """**Q5 钉子**：归档后同 code 下 ``ENABLED`` 行数为 0。"""
    v1 = make_process('W967', 1)
    v2 = make_process('W967', 2)
    v3 = make_process('W967', 3, is_latest=True)

    result = archive_process(v3)

    assert RecruitmentProcess.objects.filter(code='W967', status='ENABLED').count() == 0, (
        '只归档了一行 —— 会造出「列表页已归档、历史版本仍 ENABLED」的自相矛盾状态'
    )
    assert result['archived_version_count'] == 3
    for row in (v1, v2, v3):
        row.refresh_from_db()
        assert row.status == 'ARCHIVED'
        assert row.archived_at is not None
    assert v1.archived_at == v2.archived_at == v3.archived_at, '整条线的归档时间应统一'


def test_archive_skips_soft_deleted_rows() -> None:
    """软删行已不在任何入口里，不参与归档（改它的 status 只会污染审计）。"""
    live = make_process('W968', 1, is_latest=True)
    deleted = make_process('W968', 2)
    deleted.soft_delete()

    result = archive_process(live)

    deleted.refresh_from_db()
    assert deleted.status == 'ENABLED'
    assert result['archived_version_count'] == 1


def test_archive_refreshes_the_passed_instance() -> None:
    """``.update()`` 不回写内存实例；不刷新会让端点把「已归档」渲染成 ENABLED。"""
    process = make_process('W969', 1, is_latest=True)

    archive_process(process)

    assert process.status == 'ARCHIVED', 'archive_process 未 refresh_from_db，响应体会自相矛盾'
    assert process.archived_at is not None


def test_archive_returns_identical_shape_on_both_branches(department, hr_user) -> None:
    """**V7 钉子**：首次归档与重复归档必须返回同一套 key 与同一套类型。

    历史缺陷：早退分支的 ``reference_count`` 是 ``is_process_referenced()`` 的
    **bool** 返回值，且没有 ``archived_at`` 键。
    """
    process = make_process('W970', 1, is_latest=True)
    make_demand(process, department, hr_user, 'D-T5-004')

    first = archive_process(process)
    second = archive_process(process)

    assert set(first) == set(second) == {
        'archived', 'reference_count', 'archived_at', 'archived_version_count',
    }
    for result in (first, second):
        assert result['archived'] is True
        assert type(result['reference_count']) is int, (
            f'reference_count 是 {type(result["reference_count"]).__name__} —— '
            '早退分支返回 bool 是 V7 缺陷本体'
        )
        assert result['reference_count'] == 1
        assert isinstance(result['archived_at'], str)
    assert first['archived_at'] == second['archived_at'], '重复归档不得刷新首次归档时间'
    assert (first['archived_version_count'], second['archived_version_count']) == (1, 0)


# ============================================================
# 4. 端点层：重复归档的判据也是整条线
# ============================================================
def test_archive_endpoint_rejects_only_when_no_enabled_row_remains(auth_client) -> None:
    """``views.archive`` 的早退判据必须是「该 code 下已无 ENABLED 行」。

    老判据只看当前这一行的 status：从一个历史版本行（多半已 ARCHIVED）发起归档会被
    误判成重复归档而 409，而该线的最新版其实还是 ENABLED——真正该归档的行永远归不掉。
    """
    old_row = make_process('W971', 1, status='ARCHIVED')
    make_process('W971', 2, is_latest=True)

    resp = auth_client.post(f'/api/v1/processes/{old_row.id}/archive/')

    assert resp.status_code == 200, (
        f'从已归档的历史版本行发起归档被误判为重复归档（{resp.status_code}）—— '
        '该 code 线上还有 ENABLED 行没归掉'
    )
    assert RecruitmentProcess.objects.filter(code='W971', status='ENABLED').count() == 0

    again = auth_client.post(f'/api/v1/processes/{old_row.id}/archive/')
    assert again.status_code == StateTransitionError.status_code, '整条线都归档后应拒绝重复归档'
