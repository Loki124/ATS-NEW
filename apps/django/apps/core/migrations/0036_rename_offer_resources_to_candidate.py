"""将 Offer 资源码从 recruit:offer:* 重归属到候选人管理模块（recruit:candidate:offer:*）(2026-10-19)

背景：
  兵哥 2026-10-19 指令：Offer 功能早已并入候选人详情页 Offer 页签，系统不再含独立
  Offer 菜单 / 列表。本次重构：
    1. 重命名 4 个功能码，使其归属「候选人管理」模块、子模块设为 offer：
         recruit:offer:list     → recruit:candidate:offer:list     （查看Offer，页签读取授权）
         recruit:offer:create   → recruit:candidate:offer:create   （创建Offer）
         recruit:offer:edit     → recruit:candidate:offer:edit     （编辑Offer）
         recruit:offer:approve  → recruit:candidate:offer:approve  （发起Offer审批）
      🔴 命名遵循 V2 资源码规范（docs/DESIGN_资源编码规范.md）：
         - R4：第 1 段 == system_code（恒为 recruit）；
         - R2：第 2 段 == module 字段（candidate）。
         故新码为 recruit:candidate:offer:*（与 recruit:candidate:edit 同族），
         而非 candidate:offer:*（会触发 R2/R4 护栏失败）。
    2. 停用（≠删除）独立 Offer 菜单 recruit:offer:menu:view（status=0 + [已停用] 前缀，
       保留可追溯）；独立 Offer 列表页 / 路由 / 菜单项在前端已移除，资源码不再作为任何入口的权限码。
    3. 「Offer管理」设置配置区（recruit:settings:offer_management:menu:view，规划中）
       予以保留，本次不改动。

🔴 P0（沿用 0028 教训）：三处存储点必须在同一事务内同步，否则静默失权：
    1. permission_resources.resource_code  + module 字段
    2. role_permission.resource_code         （真实授权，漏改 = 授权全部失效）
    3. permission_templates.permission_codes （JSON 数组字面量，漏改 = 身份静默丢权）

设计要点：
  - 幂等：旧码不存在（如库已由新 seed 预置新码）时 RENAME 为 no-op；DISABLE 对
    缺失行亦 no-op。
  - 顺序无关：先 migrate 后 seed、或先 seed 后 migrate，均不冲突。migrate 改名时若
    目标码已存在（极端情况），删除旧行而非撞唯一约束。
  - 停用码补 [已停用] 前缀：0033 的加前缀逻辑在 0036 之前已执行，不会覆盖本迁移
    新停用的 recruit:offer:menu:view，故此处自行补前缀以符合 R9（禁用资源必带前缀）。
  - 不改 0026 停用的 legacy 码 recruit:offer:approve_l1/_l2（已离线、单测按字面名锁定）。
"""
from django.db import migrations

DISABLED_PREFIX = '[已停用] '


# 旧码 → (新码, 新中文名, 新类型, 新 module)
# 🔴 新码第 1 段恒为 system_code=recruit（R4），第 2 段 == module=candidate（R2），
#    子模块 offer 落在第 3 段，动作段为末段 —— 与 recruit:candidate:edit 同族。
RENAME = {
    'recruit:offer:list': ('recruit:candidate:offer:list', '查看Offer', 'BUTTON', 'candidate'),
    'recruit:offer:create': ('recruit:candidate:offer:create', '创建Offer', 'BUTTON', 'candidate'),
    'recruit:offer:edit': ('recruit:candidate:offer:edit', '编辑Offer', 'BUTTON', 'candidate'),
    'recruit:offer:approve': ('recruit:candidate:offer:approve', '发起Offer审批', 'BUTTON', 'candidate'),
}

# 独立 Offer 菜单：停用而非删除（status=0 + [已停用] 前缀，保留可追溯），
# 并清掉其孤儿授权/模板引用。
DISABLE = ['recruit:offer:menu:view']


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
    # 独立菜单的孤儿授权直接清除（该菜单已停用，授权无入口可消费）
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
        # 0033 的加前缀逻辑在 0036 之前已执行，不会覆盖本步新停用的码，
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

    # noqa 说明: renamed 是改名计数的快照，与下方 print 的口径对应。
    # 迁移已应用, 不删变量（保持历史迁移与当初执行轨迹一致）; ruff F841 卡 A6。
    renamed = sum(  # noqa: F841
        1 for old in RENAME if not Resource.objects.filter(resource_code=old).exists()
    )
    print(
        f'[0036] Offer 资源码重归属候选人管理：重命名 {len(RENAME)} 个 / '
        f'停用独立菜单 {len(DISABLE)} 个（已同步 role_permission 与 permission_templates）'
    )


def backward(apps, schema_editor):
    """反向：新码回退为旧 recruit:offer:*（menu:view 不恢复为启用，沿用停用态）。"""
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
                module='offer',
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
        ('core', '0035_remove_dynamic_strategy_assignment'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
