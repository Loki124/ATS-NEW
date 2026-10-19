"""「用户授权」资源码重归属系统设置·用户管理（recruit:settings:users:role_grant:*）(2026-10-19)

背景：
  兵哥 2026-10-19 指令 + 排查结论：独立「用户授权」页已从身份管理移除
  （与用户管理页的分配角色弹窗重复），真实入口 = 用户管理页
  (/settings/users/all) 的「身份配置」弹窗 —— 写接口
  /api/v1/permissions/users/{id}/roles/ 由 recruit:user_role:edit 守门；
  V2 契约端点 /api/v1/user-roles/ 由 recruit:user_role:list 守门。
  兵哥拍板：资源码一并迁移到 settings 家族，与用户管理归属对齐。

    1. 重命名 4 个功能码（module 同步为 settings，R2：第 2 段 == module）：
         recruit:user_role:list   → recruit:settings:users:role_grant:list   （用户身份配置列表）
         recruit:user_role:create → recruit:settings:users:role_grant:create （新增身份配置）
         recruit:user_role:edit   → recruit:settings:users:role_grant:edit   （编辑身份配置）
         recruit:user_role:delete → recruit:settings:users:role_grant:delete （撤销身份配置）
    2. 停用（≠删除）菜单码 recruit:user_role:menu:view（status=0 + [已停用] 前缀，
       保留可追溯）——独立授权菜单已无任何前端入口。

🔴 P0（沿用 0028/0036 教训）：三处存储点必须在同一事务内同步，否则静默失权：
    1. permission_resources.resource_code  + module 字段
    2. role_permission.resource_code         （真实授权，漏改 = 授权全部失效）
    3. permission_templates.permission_codes （JSON 数组字面量，漏改 = 身份静默丢权）

设计要点（与 0036 同款）：
  - 幂等：旧码不存在（库已由新 seed 预置新码）时 RENAME 为 no-op；DISABLE 缺行 no-op。
  - 顺序无关：先 migrate 后 seed、或先 seed 后 migrate，均不冲突。
  - 停用码自行补 [已停用] 前缀以符合 R9（0033 的加前缀逻辑早于本迁移执行）。
  - 不改任何 endpoint 路径（/api/v1/user-roles/、/permissions/users/{id}/roles/
    契约不变），仅权限码与守门值同步（views/alias_endpoints/测试随本次提交更新）。
"""
from django.db import migrations

DISABLED_PREFIX = '[已停用] '


# 旧码 → (新码, 新中文名, 新类型, 新 module)
# 🔴 新码第 2 段 == module=settings（R2），第 1 段恒为 system_code=recruit（R4）；
#    子模块 users（用户管理）嵌套 role_grant（身份配置授权），动作段为末段。
RENAME = {
    'recruit:user_role:list': ('recruit:settings:users:role_grant:list', '用户身份配置列表', 'BUTTON', 'settings'),
    'recruit:user_role:create': ('recruit:settings:users:role_grant:create', '新增身份配置', 'BUTTON', 'settings'),
    'recruit:user_role:edit': ('recruit:settings:users:role_grant:edit', '编辑身份配置', 'BUTTON', 'settings'),
    'recruit:user_role:delete': ('recruit:settings:users:role_grant:delete', '撤销身份配置', 'BUTTON', 'settings'),
}

# 独立授权菜单：停用而非删除（status=0 + [已停用] 前缀，保留可追溯），
# 并清掉其孤儿授权/模板引用。
DISABLE = ['recruit:user_role:menu:view']


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
    # 已停用菜单的孤儿授权直接清除（该菜单已停用，授权无入口可消费）
    RolePermission.objects.filter(resource_code__in=DISABLE).delete()


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
            elif c in DISABLE:
                changed = True  # 丢弃停用菜单的引用
            else:
                out.append(c)
        if changed:
            Template.objects.filter(pk=tpl.pk).update(permission_codes=out)


def _disable_resources(Resource):
    for code in DISABLE:
        rows = Resource.objects.filter(resource_code=code)
        if not rows.exists():
            continue  # 缺失行 → no-op（库已由新 seed 预置、无独立菜单）
        rows.update(status=0)
        # 0033 的加前缀逻辑在本迁移之前已执行，不会覆盖本步新停用的码，
        # 故此处自行补 [已停用] 前缀以满足 R9（禁用资源必带前缀）。
        for r in rows:
            if not r.resource_name.startswith(DISABLED_PREFIX):
                r.resource_name = DISABLED_PREFIX + r.resource_name
                r.save(update_fields=['resource_name'])


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    for old in RENAME:
        _rename_resource(Resource, old, RENAME[old])
    _disable_resources(Resource)
    _rename_grants(RolePermission)
    _rename_templates(Template)

    print(
        f'[0038] 用户授权资源码重归属系统设置·用户管理：重命名 {len(RENAME)} 个 / '
        f'停用菜单 {len(DISABLE)} 个（已同步 role_permission 与 permission_templates）'
    )


def backward(apps, schema_editor):
    """反向：新码回退为旧 recruit:user_role:*（menu:view 不恢复为启用，沿用停用态）。"""
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
                module='user_role',
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
        ('core', '0037_rename_position_resources_zh'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
