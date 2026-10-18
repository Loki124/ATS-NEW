"""修正 user_app_data_scope 三条资源的 module 字段（规范 R2）。2026-10-18。

背景：全量资源审计（285 条）实测唯一违规项 —— 编码第 2 段是
`user_app_data_scope`，但 `module` 字段填的是 `user_role`。后果是资源管理页
「按模块筛选」下拉里这两者语义错位（编码说"应用数据范围"、模块说"用户角色"），
且违反 `docs/DESIGN_资源编码规范.md` §4 R2。

为什么改 module 而不是改编码：
- module 字段只用于「按模块分组 / 筛选 / 展示」，改了不影响任何权限判定
  （权限判定走 resource_code 字面量）；
- 改编码则要同步 4 个权限模板的 permission_codes JSON + 前端 14 个文件里
  硬编码的码，属于「失败即静默失权」的高危改动，规范 §1 已明确不做。

幂等：可重复执行（按 resource_code 定位，不依赖旧值）。
反向：把 module 改回 user_role。
"""
from django.db import migrations

# resource_code → 正确的 module 值（必须等于编码第 2 段）
MODULE_FIXES = {
    'recruit:user_app_data_scope:menu:view': 'user_app_data_scope',
    'recruit:user_app_data_scope:list': 'user_app_data_scope',
    'recruit:user_app_data_scope:edit': 'user_app_data_scope',
}

PREV_MODULE = 'user_role'


def fix_module(apps, schema_editor):
    PermissionResource = apps.get_model('core', 'PermissionResource')
    for code, module in MODULE_FIXES.items():
        PermissionResource.objects.filter(resource_code=code).update(module=module)


def revert_module(apps, schema_editor):
    PermissionResource = apps.get_model('core', 'PermissionResource')
    PermissionResource.objects.filter(
        resource_code__in=MODULE_FIXES.keys()
    ).update(module=PREV_MODULE)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0026_disable_offline_resources'),
    ]

    operations = [
        migrations.RunPython(fix_module, revert_module),
    ]
