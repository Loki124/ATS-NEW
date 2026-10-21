"""前端菜单登记码存活护栏（2026-10-20）。

背景（兵哥 2026-10-20 排障）：
  「管理单元」页（/settings/mou）在 permissionMenu.ts 里登记的守卫码是
  `recruit:mou:menu:view` —— 该码族已被 core.0030 整族停用（status=0 + 授权清零），
  而非超管用户既拿不到这条死码、又没有 fail-open 兜底，于是菜单项被裁掉、
  直敲 URL 跳 /forbidden，尽管其角色实际持有管理单元全家授权。

  根因是「前端登记了一个后端已下线/已重命名的资源码」这一整类问题：
  纯前端改动无法感知后端码族的停用与改名，只能靠人工比对，必漏。

护栏内容：
  1. permissionMenu.ts 里登记的每一个 code，都必须在 seed 真源
     （seed_v2_init.RESOURCES）中存在 —— 不存在即死登记，直接判红。
  2. 管理单元码族必须已归入 settings 家族（recruit:settings:mgmt_unit:*），
     且旧家族 recruit:mgmt_unit:* 不得再出现在 seed 中（防种子复活，
     与 mou 族的断言同款）。

跨端读前端文件是刻意为之：本仓库是前后端一体的 monorepo，
权限码的「前端引用侧」只有在这里才能被静态校验到。
"""
import re
from pathlib import Path

import pytest

# tests → core → apps(django/apps) → django → apps → 仓库根
REPO_ROOT = Path(__file__).resolve().parents[5]
MENU_FILE = REPO_ROOT / 'web' / 'app' / 'src' / 'utils' / 'permissionMenu.ts'

# 登记行形如：{ prefix: '/settings/mou', code: 'recruit:settings:mgmt_unit:menu:view' },
CODE_PATTERN = re.compile(r"\{\s*prefix:\s*'[^']+',\s*code:\s*'([^']+)'\s*\}")


def _load_seed_resources():
    from apps.core.management.commands.seed_v2_init import RESOURCES
    return RESOURCES


def _menu_codes():
    if not MENU_FILE.exists():
        pytest.skip(f'前端菜单映射文件不存在：{MENU_FILE}')
    text = MENU_FILE.read_text(encoding='utf-8')
    return CODE_PATTERN.findall(text)


class TestMenuCodeRegistration:
    """前端 MENU_PERMISSION_RULES 登记的守卫码必须存活于 seed 真源。"""

    def test_menu_file_parsed(self):
        codes = _menu_codes()
        assert len(codes) > 30, f'解析到的登记码过少（{len(codes)}），正则可能已失效'

    def test_every_menu_code_exists_in_seed(self):
        seed_codes = {c for c, *_ in _load_seed_resources()}
        dangling = sorted({c for c in _menu_codes() if c not in seed_codes})
        assert not dangling, (
            f'前端登记了 seed 中不存在（多为已停用/已改名）的资源码，'
            f'会让菜单守卫指向死码致用户被挡在门外：{dangling}'
        )


class TestMgmtUnitFamilyMigrated:
    """管理单元码族归入 settings 家族（0042）后的真源断言。"""

    def test_new_family_present(self):
        # RESOURCES 为四元组 (code, name, type, module) → rest = [name, type, module]
        seed = {c: rest for c, *rest in _load_seed_resources()}
        for action in ('menu:view', 'list', 'create', 'edit'):
            code = f'recruit:settings:mgmt_unit:{action}'
            assert code in seed, f'seed 缺 {code}'
            module = seed[code][2]
            assert module == 'settings', f'{code} 的 module 应为 settings，实为 {module}'

    def test_old_family_absent(self):
        """旧码族不得回写 seed —— 否则重跑种子会让已迁移的码复活（R11 同款）。"""
        seed = {c for c, *_ in _load_seed_resources()}
        revived = sorted(c for c in seed if c.startswith('recruit:mgmt_unit:'))
        assert not revived, f'seed 仍含已迁移的旧 mgmt_unit 码族：{revived}'


class TestCampusControlFamilyMigrated:
    """编制管控码族重归属 campus 模块（0045）后的真源断言。"""

    def test_new_family_present(self):
        seed = {c: rest for c, *rest in _load_seed_resources()}
        for action in ('menu:view', 'list', 'edit', 'delete'):
            code = f'recruit:campus:campus_control:{action}'
            assert code in seed, f'seed 缺 {code}'
            module = seed[code][2]
            assert module == 'campus', f'{code} 的 module 应为 campus，实为 {module}'

    def test_old_family_absent(self):
        """旧码族 recruit:settings:campus_control:* 不得回写 seed —— 否则重跑种子会让已迁移的码复活。"""
        seed = {c for c, *_ in _load_seed_resources()}
        revived = sorted(c for c in seed if c.startswith('recruit:settings:campus_control:'))
        assert not revived, f'seed 仍含已迁移的旧 campus_control 码族：{revived}'


class TestApplicationFamilyMigrated:
    """「申请」码族重归属候选人管理（0048）后的真源断言。

    产品语义：Application = 候选人每次应聘记录，无独立「申请管理」页，
    故自独立 module=application 一族 6 码归位：
      - list / advance 改名 recruit:candidate:application:*（module=candidate，子模块「应聘记录」）；
      - menu:view/create/edit/reject 四码无任何端点守卫与前端调用点（menu:view 为孤儿码），
        停用不再 seed。
    """

    def test_new_family_present(self):
        seed = {c: rest for c, *rest in _load_seed_resources()}
        for action in ('list', 'advance'):
            code = f'recruit:candidate:application:{action}'
            assert code in seed, f'seed 缺 {code}'
            module = seed[code][2]
            assert module == 'candidate', f'{code} 的 module 应为 candidate，实为 {module}'

    def test_old_family_absent(self):
        """旧 recruit:application:* 码族不得回写 seed —— 改名/停用的码若回写会让迁移失效。"""
        seed = {c for c, *_ in _load_seed_resources()}
        revived = sorted(c for c in seed if c.startswith('recruit:application:'))
        assert not revived, f'seed 仍含已迁移的旧 application 码族：{revived}'
