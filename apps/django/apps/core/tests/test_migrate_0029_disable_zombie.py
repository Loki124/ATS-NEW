"""core.0029 僵尸资源停用迁移的行为测试（2026-10-18）。

迁移：`apps/core/migrations/0029_disable_zombie_resources.py`

覆盖：清单完整性（含「刻意不动的活码」反向断言）、停用置 0、幂等、反向恢复、
退出默认查询面、新库空库下不硬失败（0026 曾踩过的坑）。
"""
import importlib

import pytest
from django.apps import apps as django_apps

mig = importlib.import_module('apps.core.migrations.0029_disable_zombie_resources')


@pytest.fixture
def model():
    return django_apps.get_model('core', 'PermissionResource')


@pytest.mark.django_db
class TestListIntegrity:

    def test_no_duplicate_in_list(self):
        """清单内不得有重复码（否则 update 命中数对不上）。"""
        assert len(set(mig.ALL_CODES)) == len(mig.ALL_CODES)

    def test_two_families_disjoint(self):
        """两族清单不得交叉，避免语义混淆。"""
        assert not set(mig.ORPHAN_CODES) & set(mig.ZOMBIE_BUTTON_CODES)

    def test_role_auth_codes_not_touched(self):
        """🔴 反向断言：角色鉴权真源绝不能进停用清单。

        2026-10-20 (0043)：码族已由 recruit:role:* 归位为
        recruit:settings:permissions:roles:*（身份管理是设置中心·权限管理的
        子模块，不再是独立一级模块）。两个名字都断言，防回归。

        若误加进来，身份管理页会对所有非超管 403（permissions_v2.py 按 action 派生）。
        """
        for code in mig.ALL_CODES:
            assert not code.startswith('recruit:role:'), \
                f'recruit:role:* 是后端鉴权真源，不得停用：{code}'
            assert not code.startswith('recruit:settings:permissions:roles:'), \
                f'recruit:settings:permissions:roles:* 是后端鉴权真源，不得停用：{code}'

    def test_permission_menu_view_not_disabled(self):
        """🔴 反向断言：`settings:permissions:menu:view` 被前端菜单守卫消费，是活的。

        证据：web/app/src/utils/permissionMenu.ts:59
        停用它会让 /settings/permissions 整页对非超管不可达。
        """
        assert 'recruit:settings:permissions:menu:view' not in mig.ALL_CODES

    def test_field_acl_and_users_chain_untouched(self):
        """🔴 反向断言：现役的 field_acl / users:all 链路不得被误伤。"""
        for code in mig.ALL_CODES:
            assert 'field_acl' not in code, \
                f'field_acl 是现行字段权限唯一入口，不得停用：{code}'
            assert not code.startswith('recruit:settings:users:'), \
                f'用户管理链路是活的，不得停用：{code}'

    def test_orphan_codes_use_post_rename_underscore_names(self):
        """🔴 回归：0028 把 data-permission / user-management 改成了下划线。

        第一版 ORPHAN_CODES 仍用旧连字符名，导致 0028 改名后这 10 条残留为
        「启用态下划线僵尸」。故清单必须用改名后的下划线码，且不得再出现连字符段值。
        """
        dash = [c for c in mig.ORPHAN_CODES if '-' in c]
        assert not dash, f'孤儿码清单必须用 0028 改名后的下划线名，仍有连字符：{dash}'
        assert any('data_permission' in c for c in mig.ORPHAN_CODES)
        assert any('user_management' in c for c in mig.ORPHAN_CODES)


@pytest.mark.django_db
class TestForwardBackward:

    def _make(self, model):
        codes = mig.ALL_CODES
        for i, code in enumerate(codes):
            model.objects.create(
                resource_code=code, resource_name=f'资源{i}',
                resource_type='MENU' if code.endswith('menu:view') else 'BUTTON',
                module='settings', system_code='recruit', status=1,
            )
        return codes

    def test_disables_all(self, model):
        self._make(model)
        mig.forward(django_apps, None)
        still_on = model.objects.filter(
            resource_code__in=mig.ALL_CODES, status=1,
        ).count()
        assert still_on == 0, f'仍有 {still_on} 条未停用'

    def test_idempotent(self, model):
        self._make(model)
        mig.forward(django_apps, None)
        mig.forward(django_apps, None)
        assert model.objects.filter(
            resource_code__in=mig.ALL_CODES, status=1,
        ).count() == 0

    def test_backward_restores(self, model):
        self._make(model)
        mig.forward(django_apps, None)
        mig.backward(django_apps, None)
        assert model.objects.filter(
            resource_code__in=mig.ALL_CODES, status=1,
        ).count() == len(mig.ALL_CODES)

    def test_empty_db_does_not_crash(self, model):
        """🔴 新库/测试库天然无这些业务码，迁移必须静默通过而非硬失败。

        这是 0026 的教训：硬校验命中数会让 pytest 建库直接 1007/ERROR。
        """
        model.objects.all().delete()
        mig.forward(django_apps, None)  # 不抛异常即通过

    def test_disabled_exits_default_queryset(self, model):
        """停用后必须退出默认查询面（权限配置页只勾 status=1）。"""
        from apps.core.models_permission_v2 import PermissionResource as Live
        self._make(model)
        mig.forward(django_apps, None)
        visible = set(Live.objects.filter(status=1).values_list(
            'resource_code', flat=True))
        assert not (set(mig.ALL_CODES) & visible), \
            '停用码仍出现在默认查询面（权限配置页会继续勾选它）'
