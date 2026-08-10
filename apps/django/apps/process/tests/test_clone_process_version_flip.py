"""T2 回归：``clone_process_with_new_version`` 的版本推进 + is_latest 原子翻转。

为什么这个文件必须存在（实测证据，不是预防性补测）
====================================================
T2 的核心交付是 clone 尾部那段「先降后升」的翻转。落地后我做过一次**变异实测**：
把翻转改成「先升后降」（该写法在两库均必抛 ``IntegrityError``，等于把 clone 打死），
然后跑全量——**585 passed，全绿**。

也就是说 ``clone_process_with_new_version`` 在本仓的覆盖率是**零**：
``test_process_versioning_constraints.py`` 只在用例内部**手抄**了一遍翻转语句
（``test_demote_before_promote_succeeds``），它验证的是「DB 约束按预期拦截」，
**不是**「clone 里那段代码真的这么写了」。手抄的用例和被测代码之间没有任何连接——
生产代码改错，测试照样绿。这正是本项目反复治理的「假绿闭环 / 哑巴守卫」。

本文件把断言钉在**真实调用** ``clone_process_with_new_version`` 上，故：

- 翻转顺序写反 → :func:`test_clone_flips_is_latest_atomically` 变红（IntegrityError）
- 漏写 ``new_process.is_latest = True`` → 同一用例变红（新行不是 latest）
- 漏写老行降级 → 变红（C3' IntegrityError）
- 老行 ``current_version`` 被改写（V2 复发）→ :func:`test_clone_does_not_touch_old_row` 变红
- ``version_seq`` 用 ``process.version_seq + 1`` 而非全线 MAX+1
  → :func:`test_clone_from_historical_version_appends_to_line` 变红（撞 C1）

⚠️ 这些用例跑在 SQLite 测试库上，但结论对生产 MySQL 可信：C3' 采用表达式唯一索引
（非 partial unique），两库均真建、均拦截 ``.update()`` 旁路（详见
``test_process_versioning_constraints.py`` 头注）。
"""
from __future__ import annotations

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.process.models import RecruitmentProcess
from apps.process.services.versioning import (
    _compute_next_version,
    _compute_next_version_seq,
    clone_process_with_new_version,
)

pytestmark = pytest.mark.django_db


# ============================================================
# 工具
# ============================================================
def make_process(code: str, seq: int, *, is_latest: bool = False, **kwargs) -> RecruitmentProcess:
    """建一行流程版本。current_version 随 seq 走，避免误撞 C2。"""
    defaults = dict(
        code=code,
        name=f'{code} 流程 V{seq}',
        current_version=f'V{seq}.0',
        version_seq=seq,
        is_latest=is_latest,
        is_template=False,
        is_enabled=True,
    )
    defaults.update(kwargs)
    return RecruitmentProcess.objects.create(**defaults)


def latest_ids(code: str) -> list:
    """该 code 下 is_latest=True 的行 id（**不过滤软删**——本仓 objects 是原生 Manager）。"""
    return list(RecruitmentProcess.objects.filter(code=code, is_latest=True).values_list('id', flat=True))


# ============================================================
# 1. 纯计算函数：零副作用 + 取全线 MAX
# ============================================================
def test_compute_next_version_does_not_write_anything() -> None:
    """``_compute_next_version`` 必须是纯函数——V2 数据损坏的根因就是它当年会 save()。"""
    row = make_process('W920', 1, is_latest=True)
    before = (row.current_version, row.version_seq)

    assert _compute_next_version(row) == 'V2.0'

    row.refresh_from_db()
    assert (row.current_version, row.version_seq) == before, (
        '_compute_next_version 写库了 → V2「克隆改写老行 current_version」缺陷复发'
    )


def test_compute_next_version_is_idempotent() -> None:
    """连调多次结果恒定。老实现每调一次就 +1 一次，正是 '1.0+1+1+1' 的成因。"""
    row = make_process('W921', 1, is_latest=True)
    assert {_compute_next_version(row) for _ in range(5)} == {'V2.0'}


def test_compute_next_version_seq_takes_line_max_not_self_plus_one() -> None:
    """从历史版本发起时也必须取全线 MAX+1，否则算出的 seq 已被占用（撞 C1）。"""
    old = make_process('W922', 1, is_latest=False)
    make_process('W922', 2, is_latest=True)

    assert _compute_next_version_seq(old) == 3, 'old.version_seq + 1 == 2 已被占用'
    assert _compute_next_version(old) == 'V3.0'


def test_compute_next_version_seq_counts_soft_deleted_rows() -> None:
    """C1 是无条件唯一约束，软删行同样占位 → 计算 seq 时不得过滤软删。"""
    row = make_process('W923', 1, is_latest=True)
    soft = make_process('W923', 2, is_latest=False)
    soft.soft_delete()

    assert _compute_next_version_seq(row) == 3, '软删行被漏算 → 新行会撞 C1'


# ============================================================
# 2. clone 主路径：新行落位 + 原子翻转
# ============================================================
def test_clone_creates_new_row_on_same_code() -> None:
    """T1 去 unique 是本条的硬前置：去 unique 前这一步必 IntegrityError。"""
    old = make_process('W924', 1, is_latest=True)

    new = clone_process_with_new_version(old)

    assert new.id != old.id
    assert new.code == old.code
    assert new.version_seq == 2
    assert new.current_version == 'V2.0'
    assert new.status == 'ENABLED'
    assert RecruitmentProcess.objects.filter(code='W924').count() == 2


def test_clone_flips_is_latest_atomically() -> None:
    """**T2 核心断言**：clone 结束后 latest 唯一且落在新行上。

    翻转写反（先升后降）→ IntegrityError；漏写升级 → 新行不是 latest；
    漏写降级 → IntegrityError。三种变异都会让本用例变红。
    """
    old = make_process('W925', 1, is_latest=True)

    new = clone_process_with_new_version(old)

    old.refresh_from_db()
    new.refresh_from_db()
    assert new.is_latest is True, 'clone 漏写 new_process.is_latest = True'
    assert old.is_latest is False, 'clone 漏给老行降级'
    assert latest_ids('W925') == [new.id], 'C3\' 不变量被破坏：latest 不唯一或不在新行'


def test_clone_twice_keeps_exactly_one_latest() -> None:
    """连续克隆两次：seq 递增、latest 始终唯一且落在最新行。"""
    v1 = make_process('W926', 1, is_latest=True)

    v2 = clone_process_with_new_version(v1)
    v3 = clone_process_with_new_version(v2)

    assert [v2.version_seq, v3.version_seq] == [2, 3]
    assert [v2.current_version, v3.current_version] == ['V2.0', 'V3.0']
    assert latest_ids('W926') == [v3.id]
    assert RecruitmentProcess.objects.filter(code='W926').count() == 3


def test_clone_from_historical_version_appends_to_line() -> None:
    """从**历史**版本克隆：新行接到线尾（seq=3），而非撞已存在的 seq=2。"""
    v1 = make_process('W927', 1, is_latest=False)
    v2 = make_process('W927', 2, is_latest=True)

    v3 = clone_process_with_new_version(v1)

    assert v3.version_seq == 3
    assert v3.current_version == 'V3.0'
    v1.refresh_from_db()
    v2.refresh_from_db()
    assert (v1.is_latest, v2.is_latest, v3.is_latest) == (False, False, True)
    assert latest_ids('W927') == [v3.id]


# ============================================================
# 3. BR-103：老行只读
# ============================================================
def test_clone_does_not_touch_old_row() -> None:
    """V2 回归钉子：老行除 ``is_latest`` 外一个字段都不许被 clone 改。

    历史缺陷实测把 ``'1.0'`` 反复改写成 ``'1.0+1+1+1'``（P0 数据损坏，且经
    ``__str__`` 直达 UI）。
    """
    old = make_process('W928', 1, is_latest=True, description='老行描述', name='老行名字')
    snapshot = (old.current_version, old.version_seq, old.name, old.description, old.status)

    clone_process_with_new_version(old, new_name='新版本名字')

    old.refresh_from_db()
    assert (old.current_version, old.version_seq, old.name, old.description, old.status) == snapshot, (
        'clone 改写了老行 → 违反 BR-103「历史版本只读」，V2 缺陷复发'
    )


def test_clone_respects_explicit_new_name() -> None:
    """显式传 new_name 时用它；否则回落 ``{老名} ({新版本})``。"""
    old = make_process('W929', 1, is_latest=True, name='原始流程')

    named = clone_process_with_new_version(old, new_name='显式命名')
    assert named.name == '显式命名'

    auto = clone_process_with_new_version(named)
    assert auto.name == '显式命名 (V3.0)'


# ============================================================
# 4. 软删交互：翻转语句不过滤软删 → 自愈
# ============================================================
def test_clone_self_heals_stale_latest_on_soft_deleted_row() -> None:
    """绕过 ``soft_delete()`` override 造出的「软删行滞留 is_latest=True」，clone 应自愈。

    翻转语句 ``filter(code=...)`` 刻意不加 ``deleted_at__isnull=True``：
    真加了过滤，本用例就会因同 code 瞬时两行 latest 而 IntegrityError 变红。
    """
    stale = make_process('W930', 1, is_latest=True)
    RecruitmentProcess.objects.filter(id=stale.id).update(deleted_at=timezone.now())
    stale.refresh_from_db()
    assert stale.is_latest is True, '前置条件：软删行确实滞留了 is_latest=True'

    new = clone_process_with_new_version(stale)

    stale.refresh_from_db()
    assert stale.is_latest is False, '翻转语句过滤了软删 → 无法自愈'
    assert latest_ids('W930') == [new.id]


def test_clone_after_proper_soft_delete_succeeds() -> None:
    """走正规 ``soft_delete()`` 的流程线仍可继续克隆，且 seq 跳过软删占位。"""
    v1 = make_process('W931', 1, is_latest=True)
    v2 = clone_process_with_new_version(v1)
    v2.soft_delete()

    v3 = clone_process_with_new_version(v1)

    assert v3.version_seq == 3, '软删行占用的 seq=2 必须跳过'
    assert latest_ids('W931') == [v3.id]


# ============================================================
# 5. 关联对象深拷贝（T2 不改逻辑，仅钉住现状防回归）
# ============================================================
def test_clone_copies_stage_links_to_new_process() -> None:
    """stage_links 必须挂到**新**流程上，不得与老行共享。"""
    from apps.process.models import ProcessStageLink, RecruitmentStage, StageType

    old = make_process('W932', 1, is_latest=True)
    stage = RecruitmentStage.objects.create(code='P900', name='T2 探针初筛', stage_type=StageType.SCREEN)
    ProcessStageLink.objects.create(process=old, stage=stage, order=1, is_required=True)

    new = clone_process_with_new_version(old)

    assert new.stage_links.count() == 1
    assert old.stage_links.count() == 1, 'clone 把老行的 link 搬走了'
    assert new.stage_links.first().id != old.stage_links.first().id
    assert new.stage_links.first().stage_id == stage.id


# ============================================================
# 6. 端点层：bump-version 已废弃删除，clone-version 仍在
# ============================================================
def test_bump_version_endpoint_is_gone() -> None:
    """Q1 裁定废弃 ``bump-version``：路由与 ViewSet 方法都不得再出现。

    仅断言"函数没了"不够——DRF 的 ``@action`` 是靠路由注册暴露的，
    这里连 URL 反解一起钉死，防止有人换个方法名把端点又接回去。
    """
    from django.urls import NoReverseMatch, reverse

    from apps.process.views import RecruitmentProcessViewSet

    assert not hasattr(RecruitmentProcessViewSet, 'bump_version_action'), (
        'bump_version_action 复活了 —— 该端点已按产品 Q1 裁定废弃'
    )

    extra_actions = {a.url_path for a in RecruitmentProcessViewSet.get_extra_actions()}
    assert 'bump-version' not in extra_actions, f'bump-version 路由仍注册：{sorted(extra_actions)}'
    # 反向自检：clone-version 必须还在，否则本用例退化为「什么都没测」
    assert 'clone-version' in extra_actions, (
        'clone-version 也不见了 —— 「产生新版本」将无任何入口，本断言集失去意义'
    )

    with pytest.raises(NoReverseMatch):
        reverse('recruitmentprocess-bump-version', args=['whatever'])


def test_bump_version_symbol_removed_from_service() -> None:
    """服务层 ``bump_version`` 已改名降级为内部纯函数，旧符号不得残留。"""
    from apps.process.services import versioning

    assert not hasattr(versioning, 'bump_version'), (
        'bump_version 仍可被 import —— 它会改写老行 current_version，是 V2 数据损坏的入口'
    )
    assert hasattr(versioning, '_compute_next_version')


# ============================================================
# 7. 自检：本文件不是哑巴守卫
# ============================================================
def test_flip_order_is_actually_enforced_by_database() -> None:
    """哨兵：证明「先升后降」在当前后端**确实**会炸。

    若哪天 C3' 失效（换库/换引擎导致表达式索引被静默跳过），本用例先红——
    否则上面那些 clone 用例会退化成「怎么写都通过」的哑巴守卫。
    """
    old = make_process('W933', 1, is_latest=True)
    new = make_process('W933', 2, is_latest=False)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            new.is_latest = True
            new.save(update_fields=['is_latest'])

    old.refresh_from_db()
    assert old.is_latest is True
