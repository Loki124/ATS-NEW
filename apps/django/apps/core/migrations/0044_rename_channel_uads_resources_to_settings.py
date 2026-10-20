"""渠道管理 + 应用数据范围资源码归位系统设置家族 (2026-10-20)

背景（兵哥 2026-10-20 拍板，两项均迁 settings 家族）：

1. 渠道管理 recruit:channel:*（module=channel，4 码）：
   后端 apps/channel 是活的（/api/v1/channels/ 渠道 + /channels/costs/ 渠道成本，
   ChannelViewSet/ChannelCostViewSet 实守门），但前端零消费（无页面/无客户端/无路由，
   2026-10-11 G2 接线补码后一直是 API 先行、UI 未建状态）。兵哥裁定渠道管理归属
   设置中心子模块，码随归位，为将来设置页预留。

2. 应用数据范围 recruit:user_app_data_scope:*（module=user_app_data_scope，3 码）：
   休眠 API 能力——数据源已并入 UserRoleV2.app_data_scopes(JSON)，按 S4' 决策
   （2026-10-16）当前不开放配置（前端无入口、无写入口），守门的
   /api/v1/user-app-data-scopes/ 端点无任何页面调用。它不是任何页面的资源，
   挂在独立模块下只会让资源管理页多出一个费解的一级模块；归位 settings 家族。

    渠道（4 码）：
      recruit:channel:menu:view   → recruit:settings:channel:menu:view
      recruit:channel:list        → recruit:settings:channel:list
      recruit:channel:cost:list   → recruit:settings:channel:cost:list
      recruit:channel:cost:edit   → recruit:settings:channel:cost:edit
    应用数据范围（3 码）：
      recruit:user_app_data_scope:menu:view → recruit:settings:user_app_data_scope:menu:view
      recruit:user_app_data_scope:list      → recruit:settings:user_app_data_scope:list
      recruit:user_app_data_scope:edit      → recruit:settings:user_app_data_scope:edit

    通知中心 recruit:notification:* 保持模块级不动（/notifications 是顶栏铃铛进入的
    全局一级功能页，与候选人管理/面试管理同级，非设置子页 —— 兵哥确认）。

🔴 P0（沿用 0028/0036/0038/0043 教训）：三处存储点同一事务内同步：
    resource_code+module / role_permission.resource_code / permission_templates。
幂等、顺序无关、可反向（与 0036/0038/0043 同款模式）。
"""
from django.db import migrations


# 旧码 → (新码, 新中文名, 新类型, 新 module)
RENAME = {
    # 渠道管理 → settings:channel
    'recruit:channel:menu:view': ('recruit:settings:channel:menu:view', '渠道菜单', 'MENU', 'settings'),
    'recruit:channel:list': ('recruit:settings:channel:list', '渠道列表', 'BUTTON', 'settings'),
    'recruit:channel:cost:list': ('recruit:settings:channel:cost:list', '渠道成本列表', 'BUTTON', 'settings'),
    'recruit:channel:cost:edit': ('recruit:settings:channel:cost:edit', '渠道成本维护', 'BUTTON', 'settings'),
    # 应用数据范围 → settings:user_app_data_scope
    'recruit:user_app_data_scope:menu:view': ('recruit:settings:user_app_data_scope:menu:view', '应用数据范围菜单', 'MENU', 'settings'),
    'recruit:user_app_data_scope:list': ('recruit:settings:user_app_data_scope:list', '应用数据范围列表', 'BUTTON', 'settings'),
    'recruit:user_app_data_scope:edit': ('recruit:settings:user_app_data_scope:edit', '编辑应用数据范围', 'BUTTON', 'settings'),
}


def _rename_resource(Resource, old, new_tuple):
    new_code, new_name, new_type, new_module = new_tuple
    if not Resource.objects.filter(resource_code=old).exists():
        return  # 旧码不存在（已无数据或已被新 seed 预置新码）→ no-op
    if Resource.objects.filter(resource_code=new_code).exists():
        Resource.objects.filter(resource_code=old).delete()
        return
    Resource.objects.filter(resource_code=old).update(
        resource_code=new_code,
        resource_name=new_name,
        resource_type=new_type,
        module=new_module,
    )


def _rename_grants(RolePermission):
    for old, new_tuple in RENAME.items():
        new_code = new_tuple[0]
        for rp in RolePermission.objects.filter(resource_code=old).iterator():
            if RolePermission.objects.filter(
                role_code=rp.role_code, resource_code=new_code,
            ).exclude(pk=rp.pk).exists():
                RolePermission.objects.filter(pk=rp.pk).delete()
            else:
                RolePermission.objects.filter(pk=rp.pk).update(resource_code=new_code)


def _rename_templates(Template):
    for tpl in Template.objects.all().iterator():
        codes = tpl.permission_codes or []
        if not isinstance(codes, list):
            continue
        out, changed = [], False
        for c in codes:
            if c in RENAME:
                target = RENAME[c][0]
                if target not in out:
                    out.append(target)
                changed = True
            else:
                out.append(c)
        if changed:
            Template.objects.filter(pk=tpl.pk).update(permission_codes=out)


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    for old in RENAME:
        _rename_resource(Resource, old, RENAME[old])
    _rename_grants(RolePermission)
    _rename_templates(Template)

    print(
        f'[0044] 渠道管理 + 应用数据范围资源码归位系统设置家族：重命名 {len(RENAME)} 个'
        f'（已同步 role_permission 与 permission_templates；通知中心保持模块级不动）'
    )


def backward(apps, schema_editor):
    reverse = {v[0]: old for old, v in RENAME.items()}
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    for new_code, old in reverse.items():
        if not Resource.objects.filter(resource_code=new_code).exists():
            continue
        if Resource.objects.filter(resource_code=old).exists():
            Resource.objects.filter(resource_code=new_code).delete()
        else:
            back_module = 'channel' if ':channel:' in old else 'user_app_data_scope'
            Resource.objects.filter(resource_code=new_code).update(
                resource_code=old,
                module=back_module,
            )
    for rp in RolePermission.objects.filter(resource_code__in=reverse).iterator():
        old = reverse[rp.resource_code]
        if RolePermission.objects.filter(
            role_code=rp.role_code, resource_code=old,
        ).exclude(pk=rp.pk).exists():
            RolePermission.objects.filter(pk=rp.pk).delete()
        else:
            RolePermission.objects.filter(pk=rp.pk).update(resource_code=old)
    for tpl in Template.objects.all().iterator():
        codes = tpl.permission_codes or []
        if not isinstance(codes, list):
            continue
        out, changed = [], False
        for c in codes:
            if c in reverse:
                if reverse[c] not in out:
                    out.append(reverse[c])
                changed = True
            else:
                out.append(c)
        if changed:
            Template.objects.filter(pk=tpl.pk).update(permission_codes=out)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_rename_role_resources_to_settings_permissions'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
