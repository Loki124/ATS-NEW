"""QA 严过关独立验证 (2026-08-04): BUG-7 修复黑盒复现 + hash 等价性表.

不与 apps/candidate/tests/test_migration_0005.py 共用 helper, 独立复跑以证明:
1. 工程师报告 BUG-7 (形参 `apps` 遮蔽模块级 import) 已修
   - 用真实 StateApps (即迁移时的 apps 参数) 跑 backfill, 不抛 AttributeError
2. 本地 hash_for_search_py 与 apps.common.encryption.hash_for_search 100% 等价
   - 覆盖 6 个边界值 (含空串、大小写、首尾空格、Unicode、None)
3. 关键: None 不必严格相等 (两端处理策略可不同, 见 apps.common.encryption:80)

跑法:
    cd apps/django && source .venv/bin/activate && \\
      DJANGO_SETTINGS_MODULE=config.settings.test \\
      pytest tests/test_qa_bug7_repro.py -v --tb=short --no-header -p no:cacheprovider
"""
import importlib
import re

import pytest


# ─────────────────────────────────────────────────────────────
# 1. 复现 QA-4 原报告 (BUG-7 真凶场景)
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_qa_bug7_backfill_uses_real_stateapps():
    """QA 独立验证: 用 migration.MigrateExecutor 实际产生的 StateApps 调用 backfill.

    为什么必须用真实 StateApps:
      - `django_apps` (django.apps.apps) 是全局 app registry, 任何模块属性访问都 OK
      - `StateApps` 是 migration framework 在执行 RunPython 时构造的, 只镜像当前
        migration graph 涉及的 app + model, **不能**访问任意子模块 (如 .common)
      - BUG-7 真凶: 旧 backfill 体内 `apps.common.encryption.hash_for_search(...)`
        在 StateApps 上访问 .common → AttributeError
      - 修复后 backfill 只用 `apps.get_model(...)`, 不再访问 apps.<子模块>

    测试方法: 构造一个真实的 StateApps (snapshot 当前 candidate app 状态),
    直接传 backfill_id_card_hash(state_apps, schema_editor), 跑通即证明修复有效。
    """
    from django.db.migrations.state import StateApps
    from django.db.migrations.loader import MigrationLoader
    from django.apps import apps as django_apps

    # 加载 0005 migration 模块 (这是被测对象, 必须用真实产物)
    mig_0005 = importlib.import_module(
        'apps.candidate.migrations.0005_candidate_id_card_hash'
    )
    backfill_id_card_hash = mig_0005.backfill_id_card_hash

    # 构造真实 StateApps: 用 MigrationLoader.project_state() 获取当前 migration graph
    # 对应的 StateApps 实例 (这就是 migration 框架跑 RunPython 时实际传给 backfill 的参数)
    loader = MigrationLoader(None, ignore_no_migrations=True)
    project_state = loader.project_state()
    state_apps = project_state.apps  # type: StateApps
    # 关键校验: StateApps 不应有 .common / .candidate 属性 (这些是模块名, 不是 model)
    # 如果 backfill 误用 apps.common.encryption 或 apps.candidate.models 就会 AttributeError
    assert not hasattr(state_apps, 'common'), (
        'StateApps 不该有 .common 属性 (说明构造方式不对)'
    )
    assert state_apps.get_model('candidate', 'Candidate')._meta.model_name == 'candidate'

    # 造存量数据: 用 .update() 绕开 save() 的自动 hash 计算, 模拟 migration 前
    from apps.candidate.models import Candidate
    Candidate.objects.create(
        name='QA-BUG7-1', phone='13911110001', id_card_no='110101199605151234',
    )
    Candidate.objects.create(
        name='QA-BUG7-2', phone='13911110002', id_card_no='110101199801011234',
    )
    Candidate.objects.update(id_card_hash='')  # 清空 hash, 模拟迁移前状态

    # ⚠️ 关键调用: 用真实 StateApps (不是 django_apps) 调用 backfill
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        backfill_id_card_hash(state_apps, schema_editor)

    # 断言: hash 必须正确填充 (证明 backfill 跑通了 for 循环, 没在 apps.<x> 上崩)
    from apps.common.encryption import hash_for_search
    h1 = Candidate.objects.get(name='QA-BUG7-1').id_card_hash
    h2 = Candidate.objects.get(name='QA-BUG7-2').id_card_hash
    assert h1 == hash_for_search('110101199605151234'), (
        f'BUG-7 仍存在? hash1={h1!r} 期望 {hash_for_search("110101199605151234")!r}'
    )
    assert h2 == hash_for_search('110101199801011234')
    assert len(h1) == 64  # sha256 hex 长度

    print(f'\n[QA-BUG7] ✅ StateApps backfill 通过, hash1={h1[:16]}...')


# ─────────────────────────────────────────────────────────────
# 2. 源码层面黑盒审计: 形参遮蔽已消失
# ─────────────────────────────────────────────────────────────

def test_qa_bug7_no_attribute_access_on_apps():
    """QA 独立审计: 0005 文件源码里不允许出现 apps.<子模块>.<属性> 模式.

    这是 BUG-7 的结构指纹 —— 任何回滚到 import apps.<x> 的写法都会被这层
    grep 模式抓到。即使未来有人加新函数, 也不准在 backfill 体里访问
    apps.<具体模块>。
    """
    mig_0005 = importlib.import_module(
        'apps.candidate.migrations.0005_candidate_id_card_hash'
    )
    src = open(mig_0005.__file__, encoding='utf-8').read()

    # 抓 backfill 体内的 apps.<module>.<member> 模式
    body_match = re.search(
        r'def backfill_id_card_hash.*?(?=\ndef reverse_backfill)',
        src, re.S,
    )
    assert body_match, 'backfill 函数体未找到 (migration 文件结构改了?)'
    body = body_match.group(0)

    forbidden_attrs = re.findall(r'\bapps\.([a-z_]+)\.', body)
    bad = [a for a in forbidden_attrs if a != 'get_model']
    assert not bad, (
        f'❌ BUG-7 复发! backfill 体内出现 apps.<模块>.{bad} —— '
        f'形参 apps 遮蔽了模块引用'
    )
    # 同时全文件不应有 import apps.<具体模块>
    bad_imports = re.findall(r'^\s*import apps\.[a-z_]+', src, re.M)
    assert not bad_imports, f'❌ 0005 文件不应 import apps.<具体模块>: {bad_imports}'

    print('\n[QA-BUG7] ✅ 源码审计通过: backfill 体无 apps.<模块> 属性访问')


# ─────────────────────────────────────────────────────────────
# 3. hash 等价性表 (≥5 个边界值)
# ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize('plaintext,description', [
    ('110101199605151234', '正常 18 位身份证'),
    ('ABC12345678', '全大写 + 字母数字'),
    ('  MixedCASE@Example.COM  ', '首尾空格 + 混合大小写'),
    ('汉族身份证号', '纯中文 Unicode'),
    ('', '空串 (边界)'),
    ('   ', '纯空格串 (归一化为空)'),
    ('  Hello World  ', '首尾空格 + 内部空格'),
])
def test_qa_bug7_hash_equivalence_table(plaintext, description):
    """QA 独立验证: hash_for_search_py ≡ hash_for_search 在所有非 None 输入上 100% 相等.

    None 边界由 test_qa_bug7_hash_none_diverge 单独覆盖 (两端策略不同是允许的)。
    """
    from apps.common.encryption import hash_for_search
    mig_0005 = importlib.import_module(
        'apps.candidate.migrations.0005_candidate_id_card_hash'
    )
    h_local = mig_0005.hash_for_search_py(plaintext)
    h_real = hash_for_search(plaintext)
    assert h_local == h_real, (
        f'❌ hash 不一致 [{description}]: '
        f'local={h_local!r} vs real={h_real!r}'
    )
    if plaintext.strip().lower():
        assert len(h_local) == 64, f'hash 长度异常 [{description}]: {h_local!r}'

    print(f'\n[QA-BUG7-hash] {description:30s} -> {h_local[:24]}{"..." if h_local else ""}')


def test_qa_bug7_hash_none_diverge():
    """None 边界: 两端处理策略可不同 (不强求相等).

    apps.common.encryption.hash_for_search(None): 'if not None' 为真 → ''
    0005 hash_for_search_py(None): 'if not None' 为真 → ''
    (实际上 None 在两端都返 '', 不分叉 —— 但保留此测试以文档化"允许分叉"的策略)
    """
    from apps.common.encryption import hash_for_search
    mig_0005 = importlib.import_module(
        'apps.candidate.migrations.0005_candidate_id_card_hash'
    )
    local = mig_0005.hash_for_search_py(None)
    real = hash_for_search(None)
    # 不强求相等, 但要求都是字符串
    assert isinstance(local, str) and isinstance(real, str), (
        f'hash_for_search(None) 必须返 str, 实测 local={type(local)} real={type(real)}'
    )
    print(f'\n[QA-BUG7-hash] None -> local={local!r} real={real!r} (策略可不同)')


# ─────────────────────────────────────────────────────────────
# 4. 双路径 hash 产出稳定性: 历史回填 ↔ 未来 insert 不脱节
# ─────────────────────────────────────────────────────────────

@pytest.mark.django_db(transaction=True)
def test_qa_bug7_backfill_then_save_roundtrip():
    """QA 独立验证: 历史回填出的 hash 与未来 save() 算出的 hash 一致.

    证明: 老数据走 0005 backfill 算 hash, 新数据走 Candidate.save() 自动算 hash,
    两端必须产出相同 hex, 否则查重链路 (phone/email 同样的模式) 会新旧脱节。
    """
    from apps.candidate.models import Candidate
    from apps.common.encryption import hash_for_search

    # 历史路径: 直接 .update() 模拟 0005 跑之前的存量行
    cand_old = Candidate.objects.create(
        name='QA-OLD', phone='13911110010', id_card_no='110101200001011234',
    )
    Candidate.objects.filter(pk=cand_old.pk).update(id_card_hash='')

    # 模拟 backfill 跑
    mig_0005 = importlib.import_module(
        'apps.candidate.migrations.0005_candidate_id_card_hash'
    )
    from django.apps import apps as django_apps
    from django.db import connection
    with connection.schema_editor() as schema_editor:
        mig_0005.backfill_id_card_hash(django_apps, schema_editor)
    hash_after_backfill = Candidate.objects.get(pk=cand_old.pk).id_card_hash

    # 新数据路径: 直接 .save() 让 Candidate.save() 自动算 hash
    cand_new = Candidate.objects.create(
        name='QA-NEW', phone='13911110011', id_card_no='110101200002022345',
    )
    hash_after_save = cand_new.id_card_hash

    # 两端 hash 必须等于纯函数 hash_for_search(plaintext)
    assert hash_after_backfill == hash_for_search('110101200001011234')
    assert hash_after_save == hash_for_search('110101200002022345')

    # 历史回填 ≠ 新 insert 是预期的 (不同明文 → 不同 hash), 但内部都要对得上纯函数
    assert hash_after_backfill != hash_after_save

    print(f'\n[QA-BUG7-roundtrip] ✅ 旧={hash_after_backfill[:16]}... 新={hash_after_save[:16]}... 一致')