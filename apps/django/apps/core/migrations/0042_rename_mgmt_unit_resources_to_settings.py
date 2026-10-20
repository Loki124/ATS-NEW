"""「管理单元」资源码重归属系统设置·权限管理（recruit:settings:mgmt_unit:*）(2026-10-20)

背景（兵哥 2026-10-20 排查结论）：
  管理单元页面入口位于设置中心 → 权限管理 → 管理单元（SettingsLayout.vue:155，
  路由 /settings/mou → MouManagement.vue），但它的资源码族 `recruit:mgmt_unit:*`
  在权限目录里是与「候选人管理 / 招聘需求 / 面试管理」并列的**一级模块**
  （module='mgmt_unit'），与侧边栏归属不符 —— 兵哥据此质疑「管理单元怎么会是
  模块级别的资源」。

  更严重的是：前端菜单/路由守卫 `permissionMenu.ts` 把 `/settings/mou` 登记到了
  `recruit:mou:menu:view`（MOU 协议码族）。该族已在 0030（2026-10-18）整族停用
  （status=0 + [已停用] 前缀 + 授权清零），故非超管用户的「管理单元」菜单项被
  filterMenuByPermission 裁掉、直敲 URL 跳 /forbidden —— 而其角色实际持有
  mgmt_unit 全家授权。典型「配了权限却进不去」（前端随本次提交改为新码，
  见 permissionMenu.ts:61）。

兵哥裁决「一次性彻底解决」：资源码迁到 settings 家族，与页面归属对齐；

    1. 重命名 4 个资源码（module 同步为 settings，R2：第 2 段 == module）：
         recruit:mgmt_unit:menu:view → recruit:settings:mgmt_unit:menu:view （管理单元菜单）
         recruit:mgmt_unit:list      → recruit:settings:mgmt_unit:list      （管理单元列表）
         recruit:mgmt_unit:create    → recruit:settings:mgmt_unit:create    （新增管理单元）
         recruit:mgmt_unit:edit      → recruit:settings:mgmt_unit:edit      （编辑管理单元）
    2. 后端守卫同步（views_permission_v2.py:408 ManagementUnitViewSet）。

🔴 P0（沿用 0028/0036/0038 教训）：三处存储点必须在同一事务内同步，否则静默失权：
    1. permission_resources.resource_code + module 字段
    2. role_permission.resource_code         （真实授权，漏改 = 授权全部失效）
    3. permission_templates.permission_codes （JSON 数组字面量，漏改 = 身份静默丢权）

设计要点（与 0038 同款）：
  - 幂等：旧码不存在（库已由新 seed 预置新码）时 RENAME 为 no-op；目标已存在则删旧行。
  - 顺序无关：先 migrate 后 seed、或先 seed 后 migrate，均不冲突。
  - 不改任何 endpoint 路径（/api/v1/management-units/ 契约不变），仅权限码与守卫同步。
"""
from django.db import migrations

# 旧码 → (新码, 新中文名, 新类型, 新 module)
# 🔴 新码第 2 段 == module=settings（R2），第 1 段恒为 system_code=recruit（R4）；
#    子模块 mgmt_unit（管理单元）归属权限管理分组，动作段为末段。
RENAME = {
    'recruit:mgmt_unit:menu:view': ('recruit:settings:mgmt_unit:menu:view', '管理单元菜单', 'MENU', 'settings'),
    'recruit:mgmt_unit:list': ('recruit:settings:mgmt_unit:list', '管理单元列表', 'BUTTON', 'settings'),
    'recruit:mgmt_unit:create': ('recruit:settings:mgmt_unit:create', '新增管理单元', 'BUTTON', 'settings'),
    'recruit:mgmt_unit:edit': ('recruit:settings:mgmt_unit:edit', '编辑管理单元', 'BUTTON', 'settings'),
}


def _rename_resource(Resource, old, new_tuple):
    new_code, new_name, new_type, new_module = new_tuple
    if not Resource.objects.filter(resource_code=old).exists():
        return  # 旧码不存在（已无数据或已被新 seed 预置新码）→ no-op
    if Resource.objects.filter(resource_code=new_code).exists():
        # 目标已存在（极端顺序）：保留目标行，删除旧行，授权/模板下方会并入目标。
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
                # 授权侧无冲突语义：并入既有行，避免撞唯一约束（role_code + resource_code）
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
        f'[0042] 管理单元资源码重归属系统设置·权限管理：重命名 {len(RENAME)} 个'
        f'（已同步 role_permission 与 permission_templates）'
    )


def backward(apps, schema_editor):
    """反向：新码回退为旧 recruit:mgmt_unit:*（module 还原为 mgmt_unit）。"""
    reverse = {v[0]: (old, v[3]) for old, v in RENAME.items()}
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    for new_code, (old, _mod) in reverse.items():
        if not Resource.objects.filter(resource_code=new_code).exists():
            continue
        if Resource.objects.filter(resource_code=old).exists():
            Resource.objects.filter(resource_code=new_code).delete()
        else:
            Resource.objects.filter(resource_code=new_code).update(
                resource_code=old,
                module='mgmt_unit',
            )
    for rp in RolePermission.objects.filter(resource_code__in=reverse).iterator():
        old = reverse[rp.resource_code][0]
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
                old = reverse[c][0]
                if old not in out:
                    out.append(old)
                changed = True
            else:
                out.append(c)
        if changed:
            Template.objects.filter(pk=tpl.pk).update(permission_codes=out)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_mark_strategy_governed_batch2'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
