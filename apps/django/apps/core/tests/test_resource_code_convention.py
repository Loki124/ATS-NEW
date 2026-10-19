"""资源编码规范护栏（2026-10-18 兵哥批准立项）。

规范真源：`docs/DESIGN_资源编码规范.md`
落地真源：`apps/core/management/commands/seed_v2_init.py` 的 RESOURCES

🔴 本测试**只校验「新增」资源，不对存量报错** —— 存量 285 条里有大量历史债
   （3/4/5/6 段并存、连字符子模块等，见规范 §6），让存量违规把 CI 常驻变红
   会让护栏名存实亡。存量债务用 KNOWN_DEBT 白名单显式登记，新违规一律拦下。

校验规则（规范 §4）：
  R1  MENU 类型 ⟺ 倒数第 2 段 == 'menu'
  R2  第 2 段 == module 字段
  R3  最后 1 段 ∈ 动作受控词表
  R4  段数 >= 3 且第 1 段 == system_code
  R5  同前缀下 MENU 至多一条
  R6  模板 permission_codes 里的每个码都能在资源表找到（防悬空码 / 静默失权）
  R7  分段命名统一 snake_case（小写 + 下划线），禁连字符/大写 —— 2026-10-18 债务清零

🔴 R7 的来历：2026-10-18 之前存量有 29 个连字符段值（company-brand / field-acl …）与
   下划线族并存，同一功能存在「同名不同写法」的分叉风险。core.0028 迁移已把存量
   统一为下划线，本规则把该结论固化为不可回退的护栏 —— 分段名收敛为 snake_case 后，
   新增资源不可能再写出第二种风格。
"""
import re

import pytest
from django.conf import settings

# 动作受控词表（规范 §3.2）
ACTION_WHITELIST = {
    'view', 'list', 'create', 'edit', 'delete', 'export', 'approve', 'assign',
    'publish', 'close', 'schedule', 'feedback', 'advance', 'reject', 'start', 'stop',
    'import', 'sync', 'approve_l1', 'approve_l2',
    # 存量校园招聘工作流动作（campus 模块的 HRBP 确认 / 带教导师考核），非新增违规
    'confirm', 'evaluate',
}

# ===== 已知存量债务白名单（规范 §6）：命中即放行，但要求「债务量不增」 =====
# 2026-10-18 治理后全部清零。保留空常量作为显式基线：
# 后人若想让某类违规重新合法，必须先在此登记 —— 即「债务只减不增，且每次新增都要留下决策痕迹」。
KNOWN_DEBT_R2_MODULE_MISMATCH = set()

# 存量里动作段越界的码（规范 §6）。2026-10-18 实测为 0 —— 全部动作已收进词表。
KNOWN_ACTION_OUT_OF_WHITELIST = set()

# 🔴 分段命名的合法形态：仅小写字母、数字、下划线。
# 连字符（kebab-case）曾在存量大量存在，core.0028 已统一清除。
SEGMENT_PATTERN = re.compile(r'^[a-z0-9_]+$')


def _load_seed_resources():
    """直接读 seed 命令的 RESOURCES —— 它是新库初始化的唯一真源，
    抽样校验会漏掉后人追加的违规项，故全量校验。"""
    import importlib
    mod = importlib.import_module(
        'apps.core.management.commands.seed_v2_init'
    )
    return mod.RESOURCES


def _parts(code):
    return code.split(':')


class TestSeedResourceConvention:
    """seed_v2_init.RESOURCES 全量合规校验（新增资源必过此处）。"""

    def test_seed_not_empty(self):
        assert len(_load_seed_resources()) > 200, 'seed RESOURCES 异常为空/被清空'

    def test_no_duplicate_codes(self):
        codes = [c for c, *_ in _load_seed_resources()]
        dupes = {c for c in codes if codes.count(c) > 1}
        assert not dupes, f'seed 中存在重复资源码：{sorted(dupes)}'

    def test_r4_seg_count_and_system_prefix(self):
        """R4：段数 >= 3 且第 1 段是系统编码。"""
        for code, *_ in _load_seed_resources():
            parts = _parts(code)
            assert len(parts) >= 3, f'{code} 段数不足 3（规范要求 >= 3）'
            assert parts[0] == 'recruit', f'{code} 第 1 段应为系统编码 recruit'

    def test_r1_menu_type_matches_kind_segment(self):
        """R1：MENU 类型 ⟺ 倒数第 2 段为 menu。"""
        bad = []
        for code, _name, rtype, _module in _load_seed_resources():
            kind = _parts(code)[-2]
            if (rtype == 'MENU') != (kind == 'menu'):
                bad.append((code, rtype, kind))
        assert not bad, f'MENU 类型与 menu 种类段不一致（规范 R1）：{bad}'

    def test_r2_second_segment_equals_module_field(self):
        """R2：第 2 段必须等于 module 字段（否则按模块分组展示时语义错位）。"""
        bad = []
        for code, _name, _rtype, module in _load_seed_resources():
            if not module or code in KNOWN_DEBT_R2_MODULE_MISMATCH:
                continue
            if _parts(code)[1] != module:
                bad.append((code, _parts(code)[1], module))
        assert not bad, f'第 2 段与 module 字段不一致（规范 R2）：{bad}'

    def test_r3_action_segment_in_whitelist(self):
        """R3：动作段必须在受控词表内，否则是前端无按钮的僵尸资源。"""
        bad = [
            c for c, *_ in _load_seed_resources()
            if _parts(c)[-1] not in ACTION_WHITELIST
        ]
        assert not bad, (
            f'动作段不在受控词表（规范 R3）：{bad}；'
            f'新增动作须先更新规范 §3.2 与 ACTION_WHITELIST，并同步前端按钮'
        )

    def test_r5_one_menu_per_prefix(self):
        """R5：同一前缀（去掉末尾 kind:action）下 MENU 至多一条。"""
        seen = {}
        for code, _name, rtype, _module in _load_seed_resources():
            if rtype != 'MENU':
                continue
            prefix = ':'.join(_parts(code)[:-2])
            assert prefix not in seen, (
                f'前缀 {prefix} 下有多条 MENU：{seen.get(prefix)} 与 {code}'
            )
            seen[prefix] = code

    def test_r7_segments_snake_case_only(self):
        """R7：全部分段只能是 snake_case（小写字母/数字/下划线）。

        2026-10-18 core.0028 已把存量 29 个连字符段值统一为下划线，本规则锁死该结论。
        允许连字符会导致同一功能出现第二种写法 —— 「同名不同码」是最难排查的静默失权。
        """
        bad = []
        for code, *_ in _load_seed_resources():
            for idx, seg in enumerate(_parts(code), start=1):
                if not SEGMENT_PATTERN.match(seg):
                    bad.append(f'{code}（第 {idx} 段 `{seg}` 含非法字符）')
        assert not bad, (
            f'分段命名必须是 snake_case（规范 R7）：{bad}；'
            f'请用下划线分隔单词，不要用连字符或大写'
        )

    def test_seed_campus_split_and_rpe_present(self):
        """校招三功能拆分 + rule_engine 拆码后，seed 必须同时含两套独立码族。

        背景（docs/ARCH_校招资源码拆分与资源名对齐.md §11）：
        - campus_control / campus_ambassador / campus_session 三族各 4 码（menu/list/edit/delete）
        - resume_parser_engine 3 码（menu/list/edit）从 standard_resume 独立
        - standard_resume 仍保留（作为 1:1 授权复制源，不能被误删）
        """
        codes = {c for c, *_ in _load_seed_resources()}
        for fam in ['campus_control', 'campus_ambassador', 'campus_session']:
            for action in ['menu:view', 'list', 'edit', 'delete']:
                assert f'recruit:settings:{fam}:{action}' in codes, f'seed 缺 {fam}:{action}'
        for action in ['menu:view', 'list', 'edit']:
            assert f'recruit:settings:resume_parser_engine:{action}' in codes, \
                f'seed 缺 resume_parser_engine:{action}'
        # standard_resume 必须仍在（复制源）
        assert 'recruit:settings:standard_resume:menu:view' in codes, \
            'standard_resume 码族被误删（resume_parser_engine 的 1:1 复制源丢失）'
        # mou 整族必须从 seed 移除（0030 停用，seed 真源不再带它）
        mou_in_seed = [c for c in codes if c.startswith('recruit:mou:')]
        assert not mou_in_seed, f'seed 仍含已停用的 mou 码族：{mou_in_seed}'

    def test_r10_seed_has_no_disabled_names(self):
        """R10：seed 真源不应预置任何带 [已停用] 前缀的资源名。

        seed 全部 status=1；停用码的前缀由 0033 迁移按库内 status=0 动态打，
        不来自 seed。若 seed 里出现 [已停用] 前缀，说明有人把迁移逻辑写进了 seed，
        会导致重跑 seed 时前缀叠加或状态错乱。
        """
        DISABLED_PREFIX = '[已停用] '
        bad = [c for c, n, *_ in _load_seed_resources() if n.startswith(DISABLED_PREFIX)]
        assert not bad, f'seed 资源名含停用前缀（规范 R10）：{bad}'

    def test_r11_seed_has_no_disabled_codes(self):
        """R11：seed 真源不得预置任何已知停用码（防种子复活）。

        seed_v2_init 对 RESOURCES 内每条码无条件 `update_or_create(status=1)`。
        一旦某停用码被误写回 seed，下次跑种子即被强制启用 —— 0026/0029 的停用被无声推翻。
        本测试在源头拦截（seed 是新增资源的唯一真源）。
        """
        import importlib
        m = importlib.import_module(
            'apps.core.migrations.0033_mark_disabled_resources'
        )
        disabled = set(m.KNOWN_DISABLED_CODES)
        seed_codes = {c for c, *_ in _load_seed_resources()}
        resurrected = disabled & seed_codes
        assert not resurrected, (
            f'seed 含已停用码（重跑 seed 会被强制启用，推翻 0026/0029 停用）：'
            f'{sorted(resurrected)}'
        )

    def test_r8_frontend_one_code_one_entry(self):
        """R8：前端菜单映射「一资源码 = 一独立入口」，禁止多路径共享同一码。

        回归点：此前 /settings/resume-parser-engine 与 /settings/rule-engine
        共用 rule_engine:menu:view，拆码后必须各自独立。本测试交叉读
        permissionMenu.ts 的 MENU_PERMISSION_RULES，校验每个资源码只被一个
        前缀映射、且拆分后的四个独立码各出现且仅出现一次。
        """
        from pathlib import Path
        f = Path(settings.BASE_DIR).parent.parent / 'web' / 'app' / 'src' / 'utils' / 'permissionMenu.ts'
        assert f.exists(), f'前端权限映射文件缺失：{f}'
        text = f.read_text(encoding='utf-8')
        marker = 'MENU_PERMISSION_RULES: MenuCodeRule[] = ['
        start = text.index(marker)
        # 定位赋值处的 '= ['，避免误匹配类型注解 MenuCodeRule[] 里的 '['
        eq = text.index('= [', start)
        open_bracket = eq + 2  # 指向数组开头的 '['
        end = text.index(']', open_bracket)
        block = text[open_bracket:end]
        rules = re.findall(r"prefix:\s*'([^']+)'.*?code:\s*'([^']+)'", block, re.S)
        assert rules, '未能从 permissionMenu.ts 解析出任何菜单映射规则'

        by_code = {}
        by_prefix = {}
        for prefix, code in rules:
            by_code.setdefault(code, []).append(prefix)
            by_prefix[prefix] = code

        # 拆分后四个独立码各应恰好出现一次（一码一独立入口）
        for expected in [
            'recruit:settings:campus_control:menu:view',
            'recruit:settings:campus_ambassador:menu:view',
            'recruit:settings:campus_session:menu:view',
            'recruit:settings:resume_parser_engine:menu:view',
        ]:
            assert expected in by_code and len(by_code[expected]) == 1, \
                f'前端映射缺少/重复独立码：{expected}'

        # 硬校验：resume-parser-engine 必须独立指向 resume_parser_engine 码，
        # 绝不能与 rule-engine 共享同一码（这正是本次拆分要消除的反例）。
        # 注：candidate（/candidates + /screenings）、data_dashboard（/report + /settings/data-dashboard）
        # 等多路由共享同一 MENU 码属正常菜单聚合，不在本规则约束内。
        assert by_prefix.get('/settings/resume-parser-engine') == \
            'recruit:settings:resume_parser_engine:menu:view', \
            'resume-parser-engine 未指向 resume_parser_engine 码（与 rule_engine 仍耦合）'
        assert by_prefix.get('/settings/resume-parser-engine') != \
            'recruit:settings:rule_engine:menu:view', \
            'resume-parser-engine 仍与 rule_engine 共享同一资源码'
        assert by_prefix.get('/settings/rule-engine') == \
            'recruit:settings:rule_engine:menu:view', \
            'rule-engine 映射发生非预期变更'


@pytest.mark.django_db
class TestDbResourceConvention:
    """库内实际资源的护栏（存量白名单放行，新违规拦下）。"""

    def test_r2_no_new_module_mismatch(self):
        """R2：module 字段必须等于编码第 2 段（0027 迁移后应零违规）。"""
        from apps.core.models_permission_v2 import PermissionResource
        bad = [
            r.resource_code for r in PermissionResource.objects.all()
            if len(_parts(r.resource_code)) >= 2
            and r.module
            and _parts(r.resource_code)[1] != r.module
            and r.resource_code not in KNOWN_DEBT_R2_MODULE_MISMATCH
        ]
        assert not bad, (
            f'以下资源 module 字段与编码第 2 段不一致（规范 R2）：{bad}'
        )

    def test_r3_no_new_action_outside_whitelist(self):
        """R3：启用资源的动作段必须在受控词表内。

        存量越界项登记在 KNOWN_ACTION_OUT_OF_WHITELIST（规范 §6）。
        该白名单**只许变短不许变长** —— 新增项即视为新违规。
        """
        from apps.core.models_permission_v2 import PermissionResource
        bad = {
            r.resource_code for r in PermissionResource.objects.filter(status=1)
            if _parts(r.resource_code)[-1] not in ACTION_WHITELIST
        }
        unexpected = bad - KNOWN_ACTION_OUT_OF_WHITELIST
        assert not unexpected, (
            f'以下启用资源的动作段不在受控词表（规范 R3）：{sorted(unexpected)}；'
            f'若确需新动作，先更新规范 §3.2 + ACTION_WHITELIST + KNOWN 白名单，并同步前端按钮'
        )

    def test_r4_system_prefix_consistent(self):
        """R4：第 1 段必须等于 system_code 字段。"""
        from apps.core.models_permission_v2 import PermissionResource
        bad = [
            r.resource_code for r in PermissionResource.objects.all()
            if _parts(r.resource_code)[0] != r.system_code
        ]
        assert not bad, f'以下资源第 1 段与 system_code 不一致（规范 R4）：{bad}'

    def test_r6_template_codes_all_exist(self):
        """R6（P0）：模板里的每个码都必须在资源表中存在。

        背景：`permission_templates.permission_codes` 是 JSON 数组存码字面量，
        迁移/级联完全不覆盖它。资源被改名或删除后模板会留下悬空码 →
        该身份**静默丢失**对应功能，不报错、测不出。本测试是唯一的护栏。
        """
        from apps.core.models_permission_v2 import PermissionResource, PermissionTemplate
        existing = set(PermissionResource.objects.values_list('resource_code', flat=True))
        dangling = {}
        for tpl in PermissionTemplate.objects.all():
            missing = [c for c in (tpl.permission_codes or []) if c not in existing]
            if missing:
                dangling[tpl.template_code] = missing
        assert not dangling, (
            f'权限模板存在悬空资源码（会导致身份静默失权）：{dangling}'
        )

    def test_r7_db_segments_snake_case_only(self):
        """R7（库内）：存量资源分段已由 core.0028 统一为 snake_case，且不出现分叉。

        两重校验：
        ① 分段字符集合法；
        ② 同一「前缀 + kind:action」只存在一条资源 —— 追加这条是因为
           `company-brand:edit` 与 `company_brand:edit` 各自都满足 R1~R6，
           只有前缀比对才暴露「同名不同码」的分叉（最难排查的静默失权）。
        """
        from apps.core.models_permission_v2 import PermissionResource
        bad_segments = []
        variants = {}
        for r in PermissionResource.objects.all():
            parts = _parts(r.resource_code)
            for idx, seg in enumerate(parts, start=1):
                if not SEGMENT_PATTERN.match(seg):
                    bad_segments.append(f'{r.resource_code}（第 {idx} 段 `{seg}`）')
            if len(parts) >= 2:
                key = ':'.join(parts[:-2])
                variants.setdefault(key, []).append(r.resource_code)
        assert not bad_segments, (
            f'库内资源分段非 snake_case（规范 R7）：{sorted(set(bad_segments))}'
        )
        # 同一前缀下 kind:action 重复 = 同名不同码，必须报出来
        forked = {
            k: sorted(v) for k, v in variants.items()
            if len(v) > len({':'.join(_parts(c)[-2:]) for c in v})
        }
        assert not forked, (
            f'同一前缀下出现同名不同码的分叉（规范 R7）：{forked}'
        )

    def test_template_codes_cover_all_enabled_resources(self):
        """模板应覆盖全部启用资源（实测 4 模板覆盖 285/285）。

        反向护栏：若某资源**从未**被任何模板收录，新建模板时容易漏带，
        这里只做统计输出提醒不断言 —— 覆盖率不足未必是 bug（可能有意的窄模板）。
        """
        from apps.core.models_permission_v2 import PermissionResource, PermissionTemplate
        all_codes = set()
        for tpl in PermissionTemplate.objects.all():
            all_codes |= set(tpl.permission_codes or [])
        enabled = PermissionResource.objects.filter(status=1)
        uncovered = [
            r.resource_code for r in enabled if r.resource_code not in all_codes
        ]
        print(
            f'\n[模板覆盖] 启用 {enabled.count()} 条 / 模板收录 {len(all_codes)} 条'
            f' / 未收录 {len(uncovered)} 条'
        )

    def test_r1_menu_type_consistency_db(self):
        """R1（库内）：MENU 类型 ⟺ 倒数第 2 段为 menu。"""
        from apps.core.models_permission_v2 import PermissionResource
        bad = []
        for r in PermissionResource.objects.all():
            kind = _parts(r.resource_code)[-2] if len(_parts(r.resource_code)) >= 2 else ''
            if r.resource_type == 'MENU' and kind != 'menu':
                bad.append((r.resource_code, 'MENU 但种类段非 menu'))
            if r.resource_type != 'MENU' and kind == 'menu':
                bad.append((r.resource_code, f'{r.resource_type} 却用了 menu 段'))
        assert not bad, f'资源类型与编码种类段不一致（规范 R1）：{bad}'

    def test_r9_disabled_resources_prefixed(self):
        """R9：所有停用（status=0）资源必须带 [已停用] 前缀。

        背景：资源表无「是否停用」的独立展示标记，前端/管理员只能从名称辨识。
        0033 迁移按库内 status=0 动态给资源名加 [已停用] 前缀（幂等）。
        若某停用资源漏加前缀，管理员在权限配置界面无法区分「在用 / 停用」，
        可能误授已停用的功能。本测试锁死该结论。
        """
        from apps.core.models_permission_v2 import PermissionResource
        DISABLED_PREFIX = '[已停用] '
        bad = [
            r.resource_code for r in PermissionResource.objects.filter(status=0)
            if not r.resource_name.startswith(DISABLED_PREFIX)
        ]
        assert not bad, f'以下停用资源未加 [已停用] 前缀（规范 R9）：{bad}'


def test_convention_doc_exists():
    """规范文档是本护栏的判据来源，缺失即护栏失去依据。"""
    from pathlib import Path
    # BASE_DIR = <repo>/apps/django，文档在 <repo>/docs → 上溯两级
    doc = Path(settings.BASE_DIR).parent.parent / 'docs' / 'DESIGN_资源编码规范.md'
    assert doc.exists(), f'规范文档缺失：{doc}'
    assert '受控词表' in doc.read_text(encoding='utf-8')


@pytest.mark.django_db
class TestDisabledResourceAuthorization:
    """停用资源必须拒绝授权（即使 role_permission 残留授权行）。

    回归点：0026/0029 停用了若干功能（旧内外部用户列表 / Offer 两级审批 / 字段权限收敛后的
    孤儿码等），但 role_permission 里仍残存这些码的授权行。修复前 has_perm 不查 status →
    停用功能凭残留授权仍可访问（既违反「下线即失效」，也构成「误导性遗留状态」）。
    本测试锁死「status=0 永拒授权」，且不影响未注册码（action 派生回退码）的既有判定。
    """

    def _make_user(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        return User.objects.create(
            username='perm_disable_test', is_superuser=False, is_staff=False,
        )

    def _grant(self, user, code, status, role_code='TEST_ROLE_X'):
        from apps.core.models_permission_v2 import (
            PermissionResource, RolePermissionV2, UserRoleV2,
        )
        PermissionResource.objects.create(
            system_code='recruit', resource_code=code,
            resource_name='测试资源', resource_type='BUTTON',
            module='settings', status=status,
        )
        RolePermissionV2.objects.create(
            role_code=role_code, resource_code=code, system_code='recruit',
        )
        UserRoleV2.objects.create(
            user=user, role_code=role_code, system_code='recruit',
        )

    def test_disabled_resource_rejected_even_with_grant(self):
        from apps.core.permission_check import (
            has_perm, invalidate_disabled_codes,
        )
        user = self._make_user()
        self._grant(user, 'recruit:settings:perm_disable_test:disabled', status=0)
        invalidate_disabled_codes()  # 确保禁用码缓存含新建的停用资源
        assert has_perm(
            user, 'recruit:settings:perm_disable_test:disabled'
        ) is False

    def test_enabled_resource_granted_ok(self):
        from apps.core.permission_check import (
            has_perm, invalidate_disabled_codes,
        )
        user = self._make_user()
        self._grant(user, 'recruit:settings:perm_disable_test:enabled', status=1)
        invalidate_disabled_codes()
        assert has_perm(
            user, 'recruit:settings:perm_disable_test:enabled'
        ) is True

    def test_unknown_code_not_blocked_by_disabled_check(self):
        """未注册码（如 action 派生回退码）不受禁用检查拦截，交由既有逻辑判定。"""
        from apps.core.permission_check import (
            has_perm, invalidate_disabled_codes,
        )
        user = self._make_user()
        invalidate_disabled_codes()
        # 该码不在资源表，也不在禁用集；无授权行 → 返回 False（因无角色授权，非因禁用）
        assert has_perm(user, 'recruit:settings:not_a_real_code:view') is False
