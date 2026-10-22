"""「编制管控」资源码重归属校园招聘模块（recruit:campus:campus_control:*）(2026-10-20)

背景（兵哥 2026-10-20 排查结论）：
  编制管控（campus_control）页面入口位于「校园招聘」侧边栏分组（路由 /campus/control
  → 对应 /campus/* 菜单树），但它的资源码族 `recruit:settings:campus_control:*`
  在权限目录里 module='settings'，与侧边栏归属不符 —— 兵哥据此质疑「编制管控已经迁移
  至校园招聘下的模块级资源，怎么资源管理中还是设置中的资源」。

  根因是 0030（2026-10-18 拆分校招三功能）的设计意图：它**刻意保留**了
  `recruit:settings:campus_control:*` 这个码不变，只把前端菜单入口从「设置页」挪到
  「校园招聘」分组，导致「侧边栏分类」与「资源 module 分类」两套 taxonomy 不一致。

兵哥裁决「一次性彻底解决」：资源码迁到 campus 家族，与侧边栏归属对齐；

    1. 重命名 4 个资源码（module 同步为 campus，R2：第 2 段 == module）：
         recruit:settings:campus_control:menu:view → recruit:campus:campus_control:menu:view （编制管控菜单）
         recruit:settings:campus_control:list      → recruit:campus:campus_control:list      （编制管控列表）
         recruit:settings:campus_control:edit      → recruit:campus:campus_control:edit      （编辑编制管控）
         recruit:settings:campus_control:delete    → recruit:campus:campus_control:delete    （删除编制管控）
    2. 后端守卫同步（campus_control/views.py 三个 ViewSet + campus/views.py 复用码 mixin）。

  ⚠️ 范围只动 campus_control（编制管控）：campus_ambassador / campus_session 的侧边栏入口
     仍是 /settings/*（permissionMenu.ts:93-94），与 module='settings' 一致，不迁，
     避免制造新的不一致。

🔴 P0（沿用 0028/0036/0038/0042 教训）：三处存储点必须在同一事务内同步，否则静默失权：
    1. permission_resources.resource_code + module 字段
    2. role_permission.resource_code         （真实授权，漏改 = 授权全部失效）
    3. permission_templates.permission_codes （JSON 数组字面量，漏改 = 身份静默丢权）

设计要点（与 0042 同款）：
  - 幂等：旧码不存在（库已由新 seed 预置新码）时 RENAME 为 no-op；目标已存在则删旧行。
  - 顺序无关：先 migrate 后 seed、或先 seed 后 migrate，均不冲突。
  - 不改任何 endpoint 路径（/api/v1/.../control-* 契约不变），仅权限码与守卫同步。
"""
from django.db import migrations

# 旧码 → (新码, 新中文名, 新类型, 新 module)
# 🔴 新码第 2 段 == module=campus（R2），第 1 段恒为 system_code=recruit（R4）；
#    子模块 campus_control（编制管控）归属校园招聘分组，动作段为末段。
RENAME = {
    'recruit:settings:campus_control:menu:view': ('recruit:campus:campus_control:menu:view', '编制管控', 'MENU', 'campus'),
    'recruit:settings:campus_control:list': ('recruit:campus:campus_control:list', '编制管控列表', 'BUTTON', 'campus'),
    'recruit:settings:campus_control:edit': ('recruit:campus:campus_control:edit', '编辑编制管控', 'BUTTON', 'campus'),
    'recruit:settings:campus_control:delete': ('recruit:campus:campus_control:delete', '删除编制管控', 'BUTTON', 'campus'),
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
        f'[0045] 编制管控资源码重归属校园招聘模块：重命名 {len(RENAME)} 个'
        f'（已同步 role_permission 与 permission_templates）'
    )


def backward(apps, schema_editor):
    """反向：新码回退为旧 recruit:settings:campus_control:*（module 还原为 settings）。"""
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
                module='settings',
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
        ('core', '0044_rename_channel_uads_resources_to_settings'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
