"""core.0026_disable_offline_resources 回归护栏（2026-10-18 兵哥核查）。

背景：自助注册 / 注册审核、内外部用户独立列表、Offer 两级审批三处功能已在代码层
彻底下线，但 permission_resources 里仍留着资源项，与现役资源混列、看不出哪些已下线。

本文件锁定两条契约：
1. **清单本身**：下线资源码必须仍是库中真实存在的行（停用 ≠ 删除，资源码要可追溯）；
2. **停用语义**：这些资源必须能退出权限勾选候选（缺省查询只出 status=1）。

🔴 迁移的 disable_resources 不做「命中数硬校验」：测试库由历史迁移重放而成，
   天然没有这些业务资源码，硬校验会让 pytest 建库必然抛错。风险改由本测试覆盖 ——
   用真实 ORM 造行，再手工跑迁移函数，验证它确实把行置为 status=0。
"""
import importlib

import pytest

MIG = importlib.import_module('apps.core.migrations.0026_disable_offline_resources')


class _Apps:
    """极简 MigrationState 替身：本迁移只用到 apps.get_model。"""

    def __init__(self, model):
        self._model = model

    def get_model(self, app_label, model_name):
        assert app_label == 'core' and model_name == 'PermissionResource'
        return self._model


@pytest.fixture
def mig_module():
    return MIG


def test_disabled_codes_are_unique_and_wellformed():
    codes = MIG.DISABLED_CODES
    assert len(codes) == len(set(codes)), '下线清单有重复资源码'
    assert all(c.startswith('recruit:') for c in codes)
    # 三处下线功能的代表项必须都在清单里（防止后人误删清单条目）
    for must in (
        'recruit:settings:registrations:menu:view',   # 自助注册/注册审核
        'recruit:settings:users:internal:list',       # 内外部用户独立列表
        'recruit:offer:approve_l1',                   # Offer 两级审批
    ):
        assert must in codes


@pytest.mark.django_db
def test_disable_resources_sets_status_zero(mig_module):
    from apps.core.models_permission_v2 import PermissionResource
    # 造一行清单内资源（status=1）
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:settings:users:internal:list',
        resource_name='内部员工列表', resource_type='BUTTON',
        module='settings', status=1,
    )
    mig_module.disable_resources(_Apps(PermissionResource), None)

    row = PermissionResource.objects.get(resource_code='recruit:settings:users:internal:list')
    assert row.status == 0


@pytest.mark.django_db
def test_disable_resources_is_idempotent(mig_module):
    """可重复执行：已停用的行再跑一次不报错、状态不变。"""
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:settings:registrations:menu:view',
        resource_name='注册审核菜单', resource_type='MENU',
        module='settings', status=1,
    )
    apps = _Apps(PermissionResource)
    mig_module.disable_resources(apps, None)
    mig_module.disable_resources(apps, None)  # 第二次不应炸

    assert PermissionResource.objects.get(
        resource_code='recruit:settings:registrations:menu:view'
    ).status == 0


@pytest.mark.django_db
def test_enable_resources_reverses(mig_module):
    """反向迁移能把资源恢复为启用。"""
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:settings:users:external:list',
        resource_name='外部用户列表', resource_type='BUTTON',
        module='settings', status=0,
    )
    mig_module.enable_resources(_Apps(PermissionResource), None)

    assert PermissionResource.objects.get(
        resource_code='recruit:settings:users:external:list'
    ).status == 1


@pytest.mark.django_db
def test_disabled_resources_excluded_from_default_queryset(auth_client, mig_module):
    """停用资源退出默认查询面（= 不再进入权限勾选候选）。"""
    from apps.core.models_permission_v2 import PermissionResource
    PermissionResource.objects.create(
        system_code='recruit',
        resource_code='recruit:settings:users:create',
        resource_name='新增用户', resource_type='BUTTON',
        module='settings', status=1,
    )
    mig_module.disable_resources(_Apps(PermissionResource), None)

    resp = auth_client.get('/api/v1/permissions/resources/?module=settings&status=all')
    assert resp.status_code == 200
    data = resp.json()
    items = data['data'] if isinstance(data, dict) and 'data' in data else data
    hit = [r for r in items if r['resourceCode'] == 'recruit:settings:users:create']
    assert hit and hit[0]['status'] == 0, 'status=all 应能查到停用项（可追溯）'

    resp2 = auth_client.get('/api/v1/permissions/resources/?module=settings')
    assert resp2.status_code == 200
    data2 = resp2.json()
    items2 = data2['data'] if isinstance(data2, dict) and 'data' in data2 else data2
    assert not any(r['resourceCode'] == 'recruit:settings:users:create' for r in items2), \
        '缺省查询不应返回停用资源'
