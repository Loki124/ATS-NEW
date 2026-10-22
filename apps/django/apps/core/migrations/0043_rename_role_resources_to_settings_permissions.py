"""「身份管理(角色)」资源码归位系统设置·权限管理（recruit:settings:permissions:roles:*）(2026-10-20)

背景：
  兵哥 2026-10-20 疑问：资源管理页「按模块筛选」里，「身份管理」为什么与
  「系统设置」平级为一级模块？它不该是设置中心·权限管理下的子模块吗？

  排查结论——历史分裂脑：
    1. recruit:role:* 不是菜单码，是 RBAC API 的鉴权真源：RoleViewSet
       (/api/v1/roles/) 的 permission_required='recruit:role:list' + 按 action
       派生 create/edit/delete，另有 7 个 alias 端点用它守门；V2 立项时角色被
       当成跨设置的 RBAC 实体，独立成 module='role'。
    2. 2026-09-18 页面更名「身份管理」并入设置中心时，曾在 settings 家族建过
       一套按钮码，但与后端真源功能重复 → 零消费僵尸码（0029 已停用、刻意不
       写回 seed）。活下来的只有菜单门禁 settings:permissions:menu:view。
    3. 资源管理页的模块筛选直接读 module 字段 → 'role' 渲染成一级模块。
  净效果：菜单可见性归 settings 管，API 鉴权归 role 管——页面在 UI 里是
  子模块，在资源表里却是一级模块。

裁定（兵哥拍板）：码随模块归位。

    1. 重命名 6 个码（module 同步为 settings，R2：第 2 段 == module）：
         recruit:role:menu:view → recruit:settings:permissions:roles:menu:view
         recruit:role:list      → recruit:settings:permissions:roles:list
         recruit:role:create    → recruit:settings:permissions:roles:create
         recruit:role:edit      → recruit:settings:permissions:roles:edit
         recruit:role:delete    → recruit:settings:permissions:roles:delete
         recruit:role:assign    → recruit:settings:permissions:roles:assign
       码形与 recruit:settings:permissions:resources:*（资源管理）同构；
       资源中文名保持「角色*」（守的是角色 API，语义诚实）。
    2. 前端菜单守卫不动（用的就是 settings:permissions:menu:view，本来就是活的）。
    3. /permissions/menus/ 端点无前端调用方，其守门码 role:menu:view 随家族
       统一改名（行为不变），不做停用特判。

🔴 P0（沿用 0028/0036/0038 教训）：三处存储点必须在同一事务内同步，否则静默失权：
    1. permission_resources.resource_code  + module 字段
    2. role_permission.resource_code         （真实授权，漏改 = 授权全部失效）
    3. permission_templates.permission_codes （JSON 数组字面量，漏改 = 身份静默丢权）

设计要点（与 0036/0038 同款）：
  - 幂等：旧码不存在（库已由新 seed 预置新码）时 RENAME 为 no-op。
  - 顺序无关：先 migrate 后 seed、或先 seed 后 migrate，均不冲突。
  - 反向迁移恢复旧码（module 回 'role'）。
"""
from django.db import migrations

# 旧码 → (新码, 新中文名, 新类型, 新 module)
# 🔴 新码第 2 段 == module=settings（R2），第 1 段恒为 system_code=recruit（R4）；
#    子模块 permissions（权限管理）嵌套 roles（身份管理/角色），动作段为末段。
RENAME = {
    'recruit:role:menu:view': ('recruit:settings:permissions:roles:menu:view', '角色菜单', 'MENU', 'settings'),
    'recruit:role:list': ('recruit:settings:permissions:roles:list', '角色列表', 'BUTTON', 'settings'),
    'recruit:role:create': ('recruit:settings:permissions:roles:create', '创建角色', 'BUTTON', 'settings'),
    'recruit:role:edit': ('recruit:settings:permissions:roles:edit', '编辑角色', 'BUTTON', 'settings'),
    'recruit:role:delete': ('recruit:settings:permissions:roles:delete', '删除角色', 'BUTTON', 'settings'),
    'recruit:role:assign': ('recruit:settings:permissions:roles:assign', '分配角色', 'BUTTON', 'settings'),
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
        f'[0043] 身份管理(角色)资源码归位系统设置·权限管理：重命名 {len(RENAME)} 个'
        f'（已同步 role_permission 与 permission_templates）'
    )


def backward(apps, schema_editor):
    """反向：新码回退为旧 recruit:role:*（module 回 'role'）。"""
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
            Resource.objects.filter(resource_code=new_code).update(
                resource_code=old,
                module='role',
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
        # 0039/0040/0041/0042 为并行分支（strategy_governed 字段与 mgmt_unit 归位），
        # 本迁移不改动那些码族，直接挂到当前叶子 0042 之后。
        ('core', '0042_rename_mgmt_unit_resources_to_settings'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
