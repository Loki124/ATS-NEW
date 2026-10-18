"""core.0028 资源码分段统一迁移的行为测试（2026-10-18）。

迁移：`apps/core/migrations/0028_unify_resource_code_segments.py`

🔴 本测试是「P0 静默失权的最后一道闸」。资源码改名必须同步三处存储：
   1. permission_resources.resource_code   （资源定义本体）
   2. role_permission.resource_code         （真实授权）
   3. permission_templates.permission_codes （JSON 数组存码字面量）
任何一处漏改都是**静默**失权：不报错、日志干净、冒烟测试也未必覆盖。
故此处逐项验证三处都改到，并覆盖冲突合并、幂等、反向恢复三种边界。
"""
import importlib

import pytest
from django.apps import apps as django_apps

# 迁移模块名以数字开头（0028_…），不能用 import 语句，用 importlib 按路径加载
mig = importlib.import_module('apps.core.migrations.0028_unify_resource_code_segments')

OLD = 'recruit:settings:company_brand:edit'
# 迁移前的写法（连字符）
OLD_DASH = 'recruit:settings:company-brand:edit'
# 迁移前就有的一条无关码，用来验证「不该动的没被动」
UNTOUCHED = 'recruit:candidate:edit'


@pytest.fixture
def three_stores():
    """造出迁移前状态：资源 + 授权 + 模板 JSON 三处都含连字符码。"""
    Resource = django_apps.get_model('core', 'PermissionResource')
    RolePermission = django_apps.get_model('core', 'RolePermissionV2')
    Template = django_apps.get_model('core', 'PermissionTemplate')

    Resource.objects.all().delete()
    RolePermission.objects.all().delete()
    Template.objects.all().delete()

    Resource.objects.create(
        resource_code=OLD_DASH, resource_name='编辑品牌信息',
        resource_type='BUTTON', module='settings', system_code='recruit',
    )
    Resource.objects.create(
        resource_code=UNTOUCHED, resource_name='编辑候选人',
        resource_type='BUTTON', module='candidate', system_code='recruit',
    )
    RolePermission.objects.create(role_code='HRBP', resource_code=OLD_DASH)
    tpl = Template.objects.create(
        template_code='T_DASH', template_name='连字符模板',
        permission_codes=[OLD_DASH, UNTOUCHED], is_system=0, status=1,
    )
    return {'resource': Resource, 'rp': RolePermission, 'tpl': Template, 'tpl_id': tpl.pk}


@pytest.mark.django_db
class TestForward:

    def test_all_three_stores_renamed(self, three_stores):
        """正向主路径：资源本体与真实授权都改到新码。"""
        Resource, RP = three_stores['resource'], three_stores['rp']
        mig.forward(django_apps, None)

        assert not Resource.objects.filter(resource_code=OLD_DASH).exists(), \
            '资源本体仍残留连字符码'
        assert Resource.objects.filter(resource_code=OLD).exists(), '资源本体未改到新码'
        assert RP.objects.filter(resource_code=OLD).count() == 1, '真实授权未改到新码'

    def test_template_json_renamed(self, three_stores):
        """模板 JSON 是最容易漏的一处：它是数组字面量，不受外键/级联保护。"""
        Template = three_stores['tpl']
        mig.forward(django_apps, None)
        codes = Template.objects.get(pk=three_stores['tpl_id']).permission_codes
        assert OLD in codes, f'模板 JSON 未改到新码：{codes}'
        assert OLD_DASH not in codes, f'模板 JSON 仍残留连字符码：{codes}'
        assert UNTOUCHED in codes, '无关码被误改'

    def test_untouched_code_preserved(self, three_stores):
        """本就不含连字符的码必须原样保留（迁移不得过度改写）。"""
        Resource = three_stores['resource']
        mig.forward(django_apps, None)
        assert Resource.objects.filter(resource_code=UNTOUCHED).exists()

    def test_idempotent(self, three_stores):
        """幂等：重复跑不报错、不重复改。"""
        mig.forward(django_apps, None)
        first = three_stores['rp'].objects.count()
        mig.forward(django_apps, None)
        assert three_stores['rp'].objects.count() == first
        assert three_stores['rp'].objects.filter(resource_code=OLD).count() == 1

    def test_auth_conflict_merges_not_crashes(self, three_stores):
        """授权侧冲突：改名后目标码已存在（角色同时被授了新旧两码）→ 合并去重，不撞唯一约束。

        这是真实存在的脏数据形态：手工在库上改过码，或上一轮改名只改了资源没改授权。
        """
        RP = three_stores['rp']
        # 造冲突：同一角色同时持有新旧两码
        RP.objects.create(role_code='HRBP', resource_code=OLD)
        mig.forward(django_apps, None)
        assert RP.objects.filter(role_code='HRBP', resource_code=OLD).count() == 1, \
            '冲突授权未合并（唯一约束会被撞或出现重复）'
        assert RP.objects.filter(role_code='HRBP', resource_code=OLD_DASH).count() == 0

    def test_resource_target_conflict_aborts(self, three_stores):
        """资源侧冲突必须中止迁移并报错，而不是静默覆盖/跳过。"""
        Resource = three_stores['resource']
        Resource.objects.create(
            resource_code=OLD, resource_name='占位', resource_type='BUTTON',
            module='settings', system_code='recruit',
        )
        with pytest.raises(RuntimeError, match='目标码已存在'):
            mig.forward(django_apps, None)

    def test_uncovered_dash_segment_aborts(self, three_stores, monkeypatch):
        """🔴 回归：段映射漏覆盖时迁移必须**中止报错**，而不是跑完留一地连字符码。

        首版就是漏了 data-permission / user-management 两个段值，迁移静默跑完，
        库里残留 10 条连字符码，是靠事后人工核对才发现的。
        故用 monkeypatch 制造「库里有映射表没覆盖的段」来验证自检真能拦。
        """
        Resource = three_stores['resource']
        Resource.objects.create(
            resource_code='recruit:settings:not-mapped-seg:edit',
            resource_name='未覆盖段', resource_type='BUTTON',
            module='settings', system_code='recruit',
        )
        monkeypatch.setattr(mig, 'SEG_RENAME', {'company-brand': 'company_brand'})
        with pytest.raises(RuntimeError, match='未覆盖库内连字符段值'):
            mig.forward(django_apps, None)


@pytest.mark.django_db
class TestBackward:

    def test_reverse_restores_all_three_stores(self, three_stores):
        """反向迁移必须能把三处都还原，否则回滚后数据库与代码不一致。"""
        Resource, RP, Template = (
            three_stores['resource'], three_stores['rp'], three_stores['tpl'],
        )
        mig.forward(django_apps, None)
        mig.backward(django_apps, None)
        assert Resource.objects.filter(resource_code=OLD_DASH).exists(), '资源未还原'
        assert RP.objects.filter(resource_code=OLD_DASH).count() == 1, '授权未还原'
        codes = Template.objects.get(pk=three_stores['tpl_id']).permission_codes
        assert OLD_DASH in codes, f'模板 JSON 未还原：{codes}'


class TestRenameHelper:
    """rename_code 纯函数边界（不碰库）。"""

    def test_only_touches_mapped_segments(self):
        assert mig.rename_code('recruit:settings:company-brand:edit') == OLD
        # 本就不含连字符的码不动
        assert mig.rename_code('recruit:candidate:edit') is None
        assert mig.rename_code('recruit:settings:job_level:list') is None

    def test_renames_any_position_not_just_third(self):
        """🔴 回归：首版实现只改第 3 段，导致 data-permission / user-management
        这类「连字符段恰好落在第 3 段」的下线残留码改不掉，迁移后残留连字符码，
        护栏 R7 在真实库上失败。故现在按段值查表、不限位置。"""
        assert mig.rename_code(
            'recruit:settings:user-management:menu:view'
        ) == 'recruit:settings:user_management:menu:view'
        assert mig.rename_code(
            'recruit:settings:data-permission:edit'
        ) == 'recruit:settings:data_permission:edit'

    def test_rejects_non_string_and_none(self):
        assert mig.rename_code(None) is None
        assert mig.rename_code('') is None
        assert mig.rename_code(123) is None

    def test_unknown_segment_unchanged(self):
        """词表外的段值不动 —— 迁移不做正则通配，避免误伤未来合法码。"""
        assert mig.rename_code('recruit:settings:not-in-map:edit') is None

    def test_seg_map_is_reversible(self):
        """段映射必须无重复值，否则反向映射会丢键（静默失权）。"""
        assert len(set(mig.SEG_RENAME.values())) == len(mig.SEG_RENAME)

    def test_seg_map_covers_every_seed_segment(self):
        """🔴 段映射必须覆盖 seed 真源里全部含连字符的段值。

        这是「不把债务留到未来」的前置条件：漏一个段值 = 该段下所有码
        在真实库上残留旧写法，R7 护栏失败。
        """
        import importlib
        seed = importlib.import_module(
            'apps.core.management.commands.seed_v2_init'
        ).RESOURCES
        needed = {s for code, *_ in seed for s in code.split(':') if '-' in s}
        missing = needed - set(mig.SEG_RENAME)
        assert not missing, f'SEG_RENAME 漏覆盖 seed 中的连字符段值：{sorted(missing)}'
