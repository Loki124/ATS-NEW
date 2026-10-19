"""「岗位管理」资源中文名更正为「职位管理」（resource_name 数据迁移）。2026-10-19。

背景：
  兵哥 2026-10-19 指令：/positions 页面（PositionList）页面标题、主导航
  （Layout.vue）、创建/编辑弹窗、API 客户端注释全部叫「职位管理」，
  仅权限资源的 resource_name 还是「岗位菜单/岗位列表/创建岗位/编辑岗位/
  发布岗位/关闭岗位」，资源管理页与角色授权树展示不一致。

裁定：
  - 页面功能名 = 职位管理 → 资源中文名同步为 职位*；
  - 资源码 `recruit:position:*` **不改**：
    * R2（第2段==module='position'）与 R4（第1段==system_code）均满足；
    * 与 settings 家族的 `recruit:settings:position_*`（职位信息设置、
      职位动态字段等）英文命名同族，position 本就是「职位」的正确英文；
    * 改码需动 3 处存储点 + 大量测试，纯更名场景不值得。

迁移内容：
  仅改 permission_resources.resource_name（6 条）。中文名不进
  role_permission / permission_templates（它们只存资源码），故无需三处同步。

幂等：仅当当前名等于旧名时更新；新库由 seed 直接发新名，本迁移 no-op。
"""

from django.db import migrations

# 资源码 → (旧中文名, 新中文名)
RENAME = {
    'recruit:position:menu:view': ('岗位菜单', '职位菜单'),
    'recruit:position:list': ('岗位列表', '职位列表'),
    'recruit:position:create': ('创建岗位', '创建职位'),
    'recruit:position:edit': ('编辑岗位', '编辑职位'),
    'recruit:position:publish': ('发布岗位', '发布职位'),
    'recruit:position:close': ('关闭岗位', '关闭职位'),
}


def rename_position_names(apps, schema_editor):
    PermissionResource = apps.get_model('core', 'PermissionResource')
    for code, (old, new) in RENAME.items():
        # 仅当当前名仍为旧名时更新（幂等；防止覆盖现场已有的手工修正）
        PermissionResource.objects.filter(resource_code=code, resource_name=old).update(
            resource_name=new
        )


def revert_position_names(apps, schema_editor):
    PermissionResource = apps.get_model('core', 'PermissionResource')
    for code, (old, new) in RENAME.items():
        PermissionResource.objects.filter(resource_code=code, resource_name=new).update(
            resource_name=old
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_rename_offer_resources_to_candidate'),
    ]

    operations = [
        migrations.RunPython(rename_position_names, revert_position_names),
    ]
