"""T1 回归：RecruitmentProcess 版本化三条 DB 约束（C1 / C2 / C3'）。

背景（为什么这些用例值得写，且必须写在 DB 层）
================================================
本项目坐实过一个「假绿闭环」：``RecruitmentStage`` 的两个带 ``condition=`` 的
partial ``UniqueConstraint`` 在 SQLite 测试库真建（CI 全绿），在生产 MySQL 上被
Django **静默跳过**（``supports_partial_indexes=False``，migrate 不报错、不建索引、
不留痕迹），经 ``information_schema.STATISTICS`` 实查确认二者根本不存在。

C3' 因此改用**表达式唯一索引**：

    UniqueConstraint(Case(When(is_latest=True, then=F('code')), default=Value(None)),
                     name='uniq_one_latest_per_code')

``is_latest=True`` 的行贡献键值 ``code``，其余行贡献 ``NULL``；两库唯一索引均允许
多个 ``NULL`` → 等价于「每 code 至多 1 行 latest」。**该写法在 SQLite 与 MySQL 上
行为一致（均真建、均拦截 ``.update()`` 旁路）**，所以下面的功能性用例跑在默认
SQLite 测试库上，结论对生产可信——这正是 (d) 相对 partial unique 的关键价值。

⚠️ 但 ``supports_expression_indexes`` 是**软门槛**（要求非 MariaDB + 非 MyISAM +
MySQL >= 8.0.13）。若未来换库/换引擎，Django 会重新回到「静默跳过」的老路。
``test_backend_supports_expression_indexes`` 就是钉死这条软门槛的哨兵：一旦退化立即变红。
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from apps.process.models import RecruitmentProcess

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


def latest_count(code: str) -> int:
    """该 code 下 is_latest=True 的行数（**不过滤软删**——本仓 objects 是原生 Manager）。"""
    return RecruitmentProcess.objects.filter(code=code, is_latest=True).count()


# ============================================================
# 前置哨兵：软门槛不得退化
# ============================================================
def test_backend_supports_expression_indexes() -> None:
    """表达式索引是 C3' 的唯一实现载体，后端不支持则本文件所有断言全部失去意义。"""
    assert connection.features.supports_expression_indexes is True, (
        f'后端 {connection.vendor} 不支持表达式索引 → uniq_one_latest_per_code 会被 Django '
        f'静默跳过（不报错、不建索引），C3\' 形同虚设。'
    )


def test_versioning_constraints_really_exist_in_database() -> None:
    """向数据库**实查**：三条约束 + 复合索引必须真的建出来了。

    模型 Meta 上声明了约束、``manage.py check`` 也全绿，**都不能**证明 DB 里有东西——
    Django 在后端不支持时会静默跳过（``RecruitmentStage`` 的两条 partial unique 正是
    模型上有、MySQL 里查无此索引）。唯一可信的判据是向数据库实查。

    这里用 ``connection.introspection.get_constraints()``：它是真实的 DB 内省
    （MySQL 走 ``information_schema``，SQLite 解析 ``sqlite_master``），而非模型元数据；
    且能同时覆盖两种落地形态——MySQL 上三条都是独立索引，SQLite 上 ``fields=`` 两条
    是 ``CREATE TABLE`` 内联的具名 ``CONSTRAINT``（不出现在 ``sqlite_master`` 的 index 里）。
    """
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, 'recruitment_processes')

    required_unique = {
        'uniq_one_latest_per_code',
        'uniq_process_code_version_seq',
        'uniq_process_code_current_version',
    }
    missing = required_unique - set(constraints)
    assert not missing, (
        f'以下唯一约束在 {connection.vendor} 数据库中**不存在**（Django 很可能静默跳过了）：'
        f'{sorted(missing)}\n实有：{sorted(constraints)}'
    )
    for name in required_unique:
        assert constraints[name].get('unique') is True, f'{name} 在 DB 里不是唯一约束：{constraints[name]}'

    assert 'idx_process_code_latest' in constraints, (
        f'复合索引 idx_process_code_latest 不存在，主力查询 filter(code=..., is_latest=True) '
        f'会退化为全表扫描。实有：{sorted(constraints)}'
    )
    assert constraints['idx_process_code_latest']['columns'] == ['code', 'is_latest']

    # C3' 是表达式索引：内省拿不到具体列名（两库均报 [None]），这正是"非普通列索引"的证据
    assert constraints['uniq_one_latest_per_code']['columns'] in ([None], []), (
        f"uniq_one_latest_per_code 退化成了普通列索引：{constraints['uniq_one_latest_per_code']}"
    )

    # MySQL 专项（不单开用例、不引入 skip）：EXPRESSION 列必须非空
    if connection.vendor == 'mysql':  # pragma: no cover - 仅在 MySQL 库执行
        with connection.cursor() as cursor:
            cursor.execute(
                'SELECT EXPRESSION FROM information_schema.STATISTICS '
                'WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s',
                ['recruitment_processes', 'uniq_one_latest_per_code'],
            )
            rows = cursor.fetchall()
        assert rows, 'uniq_one_latest_per_code 在 information_schema.STATISTICS 中不存在'
        assert all(r[0] for r in rows), f'EXPRESSION 列为空 → 不是表达式索引：{rows}'


def test_expression_constraint_is_registered_on_model() -> None:
    """防「约束被人误删/改名」：模型 Meta 上必须挂着这三条约束。"""
    names = {c.name for c in RecruitmentProcess._meta.constraints}
    assert names == {
        'uniq_process_code_version_seq',
        'uniq_process_code_current_version',
        'uniq_one_latest_per_code',
    }, f'RecruitmentProcess 约束集合被改动：{names}'

    c3 = next(c for c in RecruitmentProcess._meta.constraints if c.name == 'uniq_one_latest_per_code')
    # contains_expressions=True 证明它是表达式索引而非 fields= 或 condition= 写法
    assert c3.contains_expressions is True, (
        'uniq_one_latest_per_code 必须是表达式唯一索引；'
        '严禁退回带 condition= 的 partial UniqueConstraint（MySQL 会静默跳过）'
    )
    assert not getattr(c3, 'condition', None), (
        'uniq_one_latest_per_code 不得带 condition=：MySQL supports_partial_indexes=False，'
        'Django 会静默跳过该约束，CI 全绿而生产无约束'
    )


# ============================================================
# 1. 同 code 多版本行（is_latest=False）不报错
# ============================================================
def test_multiple_versions_same_code_allowed_when_not_latest() -> None:
    make_process('W900', 1, is_latest=False)
    make_process('W900', 2, is_latest=False)
    make_process('W900', 3, is_latest=True)

    assert RecruitmentProcess.objects.filter(code='W900').count() == 3
    assert latest_count('W900') == 1


# ============================================================
# 2. 正常 save() 路径：第 2 行 latest → IntegrityError
# ============================================================
def test_second_latest_via_save_raises_integrity_error() -> None:
    make_process('W901', 1, is_latest=True)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            make_process('W901', 2, is_latest=True)

    assert latest_count('W901') == 1


# ============================================================
# 3. QuerySet.update() 绕过 save() → 同样被 DB 拦截
#    （这是 (d) 相对被淘汰的冗余列方案 (a) 的**核心收益**）
# ============================================================
def test_second_latest_via_queryset_update_raises_integrity_error() -> None:
    make_process('W902', 1, is_latest=True)
    old = make_process('W902', 2, is_latest=False)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RecruitmentProcess.objects.filter(id=old.id).update(is_latest=True)

    assert latest_count('W902') == 1


# ============================================================
# 4. bulk_update(['is_latest']) 绕过 save() → 同样被拦截
# ============================================================
def test_second_latest_via_bulk_update_raises_integrity_error() -> None:
    make_process('W903', 1, is_latest=True)
    row2 = make_process('W903', 2, is_latest=False)

    row2.is_latest = True
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RecruitmentProcess.objects.bulk_update([row2], ['is_latest'])

    assert latest_count('W903') == 1


# ============================================================
# 5. 翻转顺序：先升后降必炸、先降后升成功
# ============================================================
def test_promote_before_demote_raises() -> None:
    """先升后降：同 code 瞬时存在 2 行 latest → IntegrityError。"""
    old = make_process('W904', 1, is_latest=True)
    new = make_process('W904', 2, is_latest=False)

    with pytest.raises(IntegrityError):
        with transaction.atomic():
            # ① 先升级新行（此刻老行仍是 latest）→ 立即违反 C3'
            new.is_latest = True
            new.save(update_fields=['is_latest'])
            # ② 这行永远执行不到
            RecruitmentProcess.objects.filter(id=old.id).update(is_latest=False)

    old.refresh_from_db()
    assert old.is_latest is True
    assert latest_count('W904') == 1


def test_demote_before_promote_succeeds() -> None:
    """先降后升：T2 clone 翻转必须采用的顺序。"""
    old = make_process('W905', 1, is_latest=True)
    new = make_process('W905', 2, is_latest=False)

    with transaction.atomic():
        # ① 先降级：filter(code=...) 刻意不过滤软删，一并降级软删行（自愈）
        RecruitmentProcess.objects.filter(code=new.code).exclude(id=new.id).update(is_latest=False)
        # ② 后升级
        new.is_latest = True
        new.save(update_fields=['is_latest'])

    old.refresh_from_db()
    new.refresh_from_db()
    assert old.is_latest is False
    assert new.is_latest is True
    assert latest_count('W905') == 1


# ============================================================
# 6. 软删交互
# ============================================================
def test_soft_delete_demotes_is_latest_and_frees_the_slot() -> None:
    """soft_delete() override 必须把 is_latest 真正写库（基类 update_fields 很窄）。"""
    old = make_process('W906', 1, is_latest=True)
    new = make_process('W906', 2, is_latest=False)

    old.soft_delete()

    # 关键：从 DB 重读，证明 is_latest=False 真的落了库，而不是只改了内存对象
    old_from_db = RecruitmentProcess.objects.get(id=old.id)
    assert old_from_db.is_latest is False
    assert old_from_db.deleted_at is not None

    # 槽位已释放：同 code 的 live 行可正常升为 latest
    new.is_latest = True
    new.save(update_fields=['is_latest'])
    assert latest_count('W906') == 1


def test_bypassed_soft_delete_leaves_stale_latest_but_flip_self_heals() -> None:
    """绕过 override 直接 .update(deleted_at=...) 时，软删行会滞留 is_latest=True。

    这不是静默腐化：① 直接提升新行会抛 IntegrityError（响亮失败）；
    ② T2 的翻转语句 ``filter(code=...)`` **不过滤软删**，会连软删行一并降级 → 自愈。
    """
    stale = make_process('W907', 1, is_latest=True)
    new = make_process('W907', 2, is_latest=False)

    # 绕过 soft_delete() override，模拟他人误用
    RecruitmentProcess.objects.filter(id=stale.id).update(deleted_at=timezone.now())
    stale.refresh_from_db()
    assert stale.deleted_at is not None
    assert stale.is_latest is True, '前置条件：软删行确实滞留了 is_latest=True'

    # ① 直接提升 → 响亮失败
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            RecruitmentProcess.objects.filter(id=new.id).update(is_latest=True)

    # ② T2 翻转语句自愈（不过滤软删，连软删行一起降）
    with transaction.atomic():
        RecruitmentProcess.objects.filter(code='W907').exclude(id=new.id).update(is_latest=False)
        new.is_latest = True
        new.save(update_fields=['is_latest'])

    assert latest_count('W907') == 1
    stale.refresh_from_db()
    assert stale.is_latest is False


# ============================================================
# 7. full_clean() 友好报错，且不得误报
# ============================================================
def test_full_clean_raises_validation_error_on_duplicate_latest() -> None:
    make_process('W908', 1, is_latest=True)
    dup = RecruitmentProcess(
        code='W908', name='重复 latest', current_version='V2.0',
        version_seq=2, is_latest=True,
    )
    with pytest.raises(ValidationError) as exc:
        dup.full_clean()
    assert '同一流程线（code）只能有一个最新版本（is_latest=True）' in str(exc.value)


def test_full_clean_no_false_positive_on_historical_version() -> None:
    """历史版本（is_latest=False）不得被误报。"""
    make_process('W909', 1, is_latest=True)
    hist = RecruitmentProcess(
        code='W909', name='历史版本', current_version='V2.0',
        version_seq=2, is_latest=False,
    )
    hist.full_clean()  # 不抛异常即为通过


def test_full_clean_no_false_positive_on_different_code() -> None:
    """不同 code 各自持有 latest，不得被误报。"""
    make_process('W910', 1, is_latest=True)
    other = RecruitmentProcess(
        code='W911', name='另一条流程线', current_version='V1.0',
        version_seq=1, is_latest=True,
    )
    other.full_clean()


def test_full_clean_no_false_positive_on_self_resave() -> None:
    """自身重存（latest 行 full_clean 自己）不得被误报为与自己冲突。"""
    row = make_process('W912', 1, is_latest=True)
    row.refresh_from_db()
    row.description = '改个描述再存'
    row.full_clean()
    row.save()


# ============================================================
# 8. C1 / C2 两条复合唯一约束各自生效
# ============================================================
def test_unique_code_version_seq_enforced() -> None:
    make_process('W913', 1, is_latest=True)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            # version_seq 撞车（current_version 刻意错开，隔离出 C1）
            make_process('W913', 1, is_latest=False, current_version='V9.9')
    assert RecruitmentProcess.objects.filter(code='W913').count() == 1


def test_unique_code_current_version_enforced() -> None:
    make_process('W914', 1, is_latest=True)
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            # current_version 撞车（version_seq 刻意错开，隔离出 C2）
            make_process('W914', 2, is_latest=False, current_version='V1.0')
    assert RecruitmentProcess.objects.filter(code='W914').count() == 1


def test_same_version_seq_across_different_codes_allowed() -> None:
    """C1/C2 均以 code 分组，跨 code 的相同 seq / 版本串必须放行。"""
    make_process('W915', 1, is_latest=True)
    make_process('W916', 1, is_latest=True)
    assert RecruitmentProcess.objects.filter(version_seq=1, current_version='V1.0').count() == 2


# ============================================================
# 附：current_version default 与写入点一致性
# ============================================================
def test_current_version_default_is_v_prefixed() -> None:
    """default 与解析逻辑必须对同一格式达成一致。

    V3 缺陷根因即 default='1.0' 与要求 startswith('V') 的解析逻辑不匹配，
    导致默认路径掉进 bug 分支，版本号被拼成 '1.0+1+1+…'。
    """
    field = RecruitmentProcess._meta.get_field('current_version')
    assert field.default == 'V1.0'

    row = RecruitmentProcess.objects.create(code='W917', name='走默认版本号')
    assert row.current_version == 'V1.0'


def test_code_is_not_unique_anymore() -> None:
    """去 unique 是同 code 多版本（以及 T3 clone）的硬前置，防被人改回去。"""
    assert RecruitmentProcess._meta.get_field('code').unique is False
