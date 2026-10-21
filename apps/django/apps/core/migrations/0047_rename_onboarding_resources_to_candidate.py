"""将待入职资源码重归属候选人管理模块（recruit:candidate:onboarding:*），中文名同步「录用信息」(2026-10-21)

背景（兵哥 2026-10-21 指令）：
  待入职功能已并入候选人详情页「录用信息」页签（原全局「待入职」列表页 / 路由 /
  菜单项已移除，前端提交 b28713e4；页签名随后由「待入职」调整为「录用信息」）。
  资源目录仍残留独立的 module='onboarding'（入职管理）一族 4 码，与产品归属不符。
  本次按 0036（Offer 并入候选人管理）同款先例处置：

    1. 重命名 3 个功能码，使其归属「候选人管理」模块、子模块「录用信息」：
         recruit:onboarding:list   → recruit:candidate:onboarding:list   （录用信息列表，页签读取授权）
         recruit:onboarding:create → recruit:candidate:onboarding:create （创建录用信息）
         recruit:onboarding:edit   → recruit:candidate:onboarding:edit   （编辑录用信息）
      🔴 命名遵循 V2 资源码规范（docs/DESIGN_资源编码规范.md）：
         - R4：第 1 段 == system_code（恒为 recruit）；
         - R2：第 2 段 == module 字段（candidate）。
         故新码为 recruit:candidate:onboarding:*（与 recruit:candidate:offer:* 同构）。
         码段保留 onboarding（与后端 Onboarding 模型 / /api/v1/onboardings/ 路由同源），
         仅中文名同步页签「录用信息」，sub_module 同步置「录用信息」。
    2. 停用（≠删除）独立「入职菜单」recruit:onboarding:menu:view（status=0 +
       [已停用] 前缀，保留可追溯）；全局待入职入口已随 b28713e4 移除，该菜单码
       不再作为任何入口的权限码，其孤儿授权/模板引用一并清除。
    3. sub_module 置位：0046 已为 PermissionResource 加 sub_module 列（候选人管理
       10 条置位），本迁移为 3 条新码补置「录用信息」（与 RESOURCE_SUB_MODULES
       真源一致；存量库由此迁移负责，全新库由 seed_v2_init 承担，双路径同 0046）。

🔴 P0（沿用 0028/0036/0038/0042/0044 教训）：三处存储点必须在同一事务内同步，否则静默失权：
    1. permission_resources.resource_code + module 字段
    2. role_permission.resource_code         （真实授权，漏改 = 授权全部失效）
    3. permission_templates.permission_codes （JSON 数组字面量，漏改 = 身份静默丢权）

设计要点（与 0036/0044 同款）：
  - 幂等：旧码不存在（库已由新 seed 预置新码）时 RENAME 为 no-op；DISABLE 对缺失行
    亦 no-op；sub_module 置位为无条件 update，重复执行结果一致。
  - 顺序无关：先 migrate 后 seed、或先 seed 后 migrate，均不冲突。
  - 不改任何 endpoint 路径（/api/v1/onboardings/* 契约不变），仅权限码与守卫同步。
"""
from django.db import migrations

DISABLED_PREFIX = '[已停用] '


# 旧码 → (新码, 新中文名, 新类型, 新 module, 新 sub_module)
# 🔴 新码第 1 段恒为 system_code=recruit（R4），第 2 段 == module=candidate（R2）；
#    子模块 onboarding（展示名「录用信息」）落在第 3 段，动作段为末段
#    —— 与 recruit:candidate:offer:* 同构。
RENAME = {
    'recruit:onboarding:list': ('recruit:candidate:onboarding:list', '录用信息列表', 'BUTTON', 'candidate', '录用信息'),
    'recruit:onboarding:create': ('recruit:candidate:onboarding:create', '创建录用信息', 'BUTTON', 'candidate', '录用信息'),
    'recruit:onboarding:edit': ('recruit:candidate:onboarding:edit', '编辑录用信息', 'BUTTON', 'candidate', '录用信息'),
}

# 独立「入职菜单」：停用而非删除（status=0 + [已停用] 前缀，保留可追溯），
# 并清掉其孤儿授权/模板引用（全局待入职入口已随前端 b28713e4 移除）。
DISABLE = ['recruit:onboarding:menu:view']


def _rename_resource(Resource, old, new_tuple):
    new_code, new_name, new_type, new_module, new_sub = new_tuple
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
        sub_module=new_sub,
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
        # 0033 的加前缀逻辑早已执行，不会覆盖本迁移新停用的码，
        # 故此处自行补 [已停用] 前缀以满足 R9（禁用资源必带前缀）。
        for r in rows:
            if not r.resource_name.startswith(DISABLED_PREFIX):
                r.resource_name = DISABLED_PREFIX + r.resource_name
                r.save(update_fields=['resource_name'])


def _ensure_sub_module(Resource):
    """无条件置位 sub_module（幂等）：覆盖「目标行已存在被跳过改名」的极端顺序。"""
    for old, new_tuple in RENAME.items():
        new_code, _, _, _, new_sub = new_tuple
        Resource.objects.filter(resource_code=new_code).update(sub_module=new_sub)


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    for old in RENAME:
        _rename_resource(Resource, old, RENAME[old])
    _disable_resources(Resource)
    _ensure_sub_module(Resource)
    _rename_grants(RolePermission)
    _rename_templates(Template)

    print(
        f'[0047] 待入职资源码重归属候选人管理：重命名 {len(RENAME)} 个 / '
        f'停用独立菜单 {len(DISABLE)} 个（已同步 role_permission、permission_templates 与 sub_module）'
    )


def backward(apps, schema_editor):
    """反向：新码回退为旧 recruit:onboarding:*（menu:view 不恢复为启用，沿用停用态；
    sub_module 回置 NULL——旧码此前不在 0046 置位清单内，原初即空）。"""
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
                resource_name={'recruit:onboarding:list': '入职列表',
                               'recruit:onboarding:create': '创建入职',
                               'recruit:onboarding:edit': '编辑入职'}[old],
                module='onboarding',
                sub_module=None,
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
        ('core', '0046_permissionresource_sub_module'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
