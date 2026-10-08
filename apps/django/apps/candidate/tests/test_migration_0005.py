"""BUG-7 回归测试：migration 0005 backfill 在有数据时必须真的跑。

QA-4 在 round-2/3 重跑确认：原 0005_candidate_id_card_hash.py 的 backfill 形参
`apps` 把模块级 `import apps.common.encryption` 遮蔽了。:memory: 测试 DB 无候选
人行 -> for 循环空跑 -> `apps.common.encryption` 永不被求值 -> 全量测试 345 passed
但生产 migrate 直接 AttributeError。本测试故意让 backfill 真正执行非空迭代,
把 BUG-7 钉死。

另外覆盖：
- hash 产出与 apps.common.encryption.hash_for_search 100% 一致 (保证历史回填
  与未来 insert 同 hash, 查重链路不断)
- 身份证为空 / 缺失的行被正确跳过 (id_card_hash 留空串)
- reverse callback 正确清空 hash
"""
# 直接按文件路径 import 0005 (Django migrations 包不会 re-export migration 函数)
import importlib
import os
import re

import pytest

_mig_0005 = importlib.import_module('apps.candidate.migrations.0005_candidate_id_card_hash')
backfill_id_card_hash = _mig_0005.backfill_id_card_hash
reverse_backfill_id_card_hash = _mig_0005.reverse_backfill_id_card_hash
hash_for_search_py = _mig_0005.hash_for_search_py

from apps.common.encryption import LEGACY_HASH_SALT, hash_for_search


def _migration_era_hash(plaintext):
    """migration 0005 时期的哈希值。

    2026-09-27 P0-2: hash_for_search 的 salt 已外置为 PII_HASH_SALT; 但 0005 是
    **已冻结的历史迁移**, 其本地 hash_for_search_py 恒用旧 salt。所以凡是与
    "迁移回填结果" 对比的断言, 都必须显式传 LEGACY_HASH_SALT, 不能依赖当前
    配置 (否则一旦启用新 salt, 这里就会误报 —— 实际是测试口径错了, 不是代码错)。
    """
    return hash_for_search(plaintext, LEGACY_HASH_SALT)
from apps.candidate.models import Candidate

# ─────────────────────────────────────────────────────────────
# 1. 形参遮蔽不复存在：backfill 源码层面不能再访问 apps.<module>
# ─────────────────────────────────────────────────────────────

def test_backfill_signature_no_shadow_import():
    """源码层面保证形参 `apps` 不会再遮蔽任何模块引用。

    反证: 如果有人误回滚到 import apps.common.encryption 的写法, 本断言失败。
    关键: `apps.get_model(...)` 是合法的 (Django migration 标准用法),
    `apps.<具体模块>` 是非法的 (形参遮蔽模块)。
    """
    src = open(_mig_0005.__file__).read()
    body_match = re.search(
        r'def backfill_id_card_hash.*?(?=\ndef reverse_backfill)',
        src, re.S,
    )
    assert body_match, 'backfill body 找不到'
    body = body_match.group(0)
    # 不允许: apps.<小写模块名>.<成员> 模式
    forbidden = re.findall(r'\bapps\.([a-z_]+)\.', body)
    bad = [a for a in forbidden if a != 'get_model']
    assert not bad, (
        f'backfill 体内仍有 apps.<模块>.<成员> 访问: {bad} '
        f'(形参 apps 把模块级 import 遮蔽)'
    )


def test_no_apps_module_level_import():
    """进一步保险: 整个 0005 文件都不该 import apps.<具体模块>。"""
    src = open(_mig_0005.__file__).read()
    bad_imports = re.findall(r'^import apps\.[a-z_]+', src, re.M)
    assert not bad_imports, f'0005 文件不应 import apps.<模块>: {bad_imports}'


# ─────────────────────────────────────────────────────────────
# 2. 本地 hash_for_search_py 与 apps.common.encryption.hash_for_search 完全等价
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize('plaintext', [
    '110101199605151234',
    'ABC12345678',
    '  MixedCASE@Example.COM  ',  # 大小写 + 空白
    '汉族身份证号',  # Unicode
    '',  # 空值
    None,  # None
])
def test_local_hash_matches_real_hash(plaintext):
    """本地复刻必须与真实实现产出完全相同的 hex, 否则历史回填与新 insert 错位。"""
    assert hash_for_search_py(plaintext) == _migration_era_hash(plaintext)


# ─────────────────────────────────────────────────────────────
# 3. 真跑 backfill with 非空数据: 把 BUG-7 钉死
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_backfill_runs_with_real_data(django_db_serialized_rollback):
    """直接调用 backfill, 用 Django 的全局 app registry 作为 apps 参数。
    BUG-7 真凶场景: 非空 for 循环真正执行到 `c.id_card_hash = hash_for_search_py(id_card)`。

    原版本这里会抛 AttributeError: 'StateApps' object has no attribute 'common'
    因为 `apps.common.encryption.hash_for_search(...)` 访问的是 StateApps.common。

    ⚠️ 2026-08-04 QA 严过关 fix: Candidate.save() 会自动从 id_card_no 算出
    id_card_hash (见 apps/candidate/models.py:130-163), 所以 ORM 新建的候选
    人已经带着 hash, 不能代表 "migration 跑之前" 的状态。这里用
    Candidate.objects.update(id_card_hash='') 把 hash 清空, 模拟存量行
    (BUG-7 真凶场景就是这些存量行), 然后 backfill 必须把它们算出来。
    此外 id_card_no 字段是 EncryptedCharField(blank=True 但 NOT NULL), 所以
    空值用 '' 而非 None (None 在 SQLite NOT NULL 约束下直接 IntegrityError)。
    """
    # 造一批数据: 含 id_card_no / 空串 两种情况 (None 不行, NOT NULL)
    Candidate.objects.create(name='张三', phone='13900000001',
                              id_card_no='110101199605151234')
    Candidate.objects.create(name='李四', phone='13900000002',
                              id_card_no='110101199801011234')
    Candidate.objects.create(name='王五-无身份证', phone='13900000003',
                              id_card_no='')
    Candidate.objects.create(name='赵六-空身份证', phone='13900000004',
                              id_card_no='')

    # 模拟 migration 跑之前的状态: 清空所有 hash (绕过 Candidate.save() 的
    # 自动 hash 计算, 让 backfill 成为 hash 的唯一来源)
    Candidate.objects.update(id_card_hash='')
    assert Candidate.objects.filter(id_card_hash__gt='').count() == 0  # 起始未回填

    # 用 Django 全局 app registry 作为 apps 参数 (StateApps.get_model 也支持)
    from django.apps import apps as django_apps
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        backfill_id_card_hash(django_apps, schema_editor)

    # 验证: 有身份证的行 hash 正确, 空/None 的行 hash 为 ''
    zhangsan = Candidate.objects.get(name='张三')
    assert zhangsan.id_card_hash == _migration_era_hash('110101199605151234')
    assert len(zhangsan.id_card_hash) == 64

    lisi = Candidate.objects.get(name='李四')
    assert lisi.id_card_hash == _migration_era_hash('110101199801011234')

    wangwu = Candidate.objects.get(name='王五-无身份证')
    assert wangwu.id_card_hash == ''  # 跳过

    zhaoliu = Candidate.objects.get(name='赵六-空身份证')
    assert zhaoliu.id_card_hash == ''  # 跳过


@pytest.mark.django_db(transaction=True)
def test_reverse_backfill_clears_hashes(django_db_serialized_rollback):
    """reverse callback: 清空所有 id_card_hash。"""
    Candidate.objects.create(name='A', phone='13900000010',
                              id_card_no='110101199605151235')
    Candidate.objects.create(name='B', phone='13900000011',
                              id_card_no='110101199801011235')

    from django.apps import apps as django_apps
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        backfill_id_card_hash(django_apps, schema_editor)

    assert Candidate.objects.get(name='A').id_card_hash != ''
    assert Candidate.objects.get(name='B').id_card_hash != ''

    with connection.schema_editor() as schema_editor:
        reverse_backfill_id_card_hash(django_apps, schema_editor)

    assert Candidate.objects.get(name='A').id_card_hash == ''
    assert Candidate.objects.get(name='B').id_card_hash == ''


@pytest.mark.django_db(transaction=True)
def test_backfill_idempotent(django_db_serialized_rollback):
    """连续跑两次 backfill, 结果必须一致 (幂等)。"""
    Candidate.objects.create(name='X', phone='13900000020',
                              id_card_no='110101199605151236')

    from django.apps import apps as django_apps
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        backfill_id_card_hash(django_apps, schema_editor)
    first_hash = Candidate.objects.get(name='X').id_card_hash

    with connection.schema_editor() as schema_editor:
        backfill_id_card_hash(django_apps, schema_editor)
    second_hash = Candidate.objects.get(name='X').id_card_hash

    assert first_hash == second_hash
    assert first_hash == _migration_era_hash('110101199605151236')


# ─────────────────────────────────────────────────────────────
# 4. 防回滚保险: 如果有人改回 import apps.common.encryption, 上面所有非空测试
#    会因 AttributeError 失败。本文件本身就是 regression suite 的一部分。
# ─────────────────────────────────────────────────────────────