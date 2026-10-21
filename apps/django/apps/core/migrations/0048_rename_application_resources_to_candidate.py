"""将「申请」资源码重归属候选人管理模块（recruit:candidate:application:*），中文名同步「应聘记录」(2026-10-21)

背景（兵哥 2026-10-21 指令）：
  「申请」(Application) 的产品语义 = 候选人的每次应聘记录（候选人详情页展示多次投递、
  每次对应不同职位/流程线），数据只被候选人管理页消费；系统里**不存在**独立的
  「申请管理」页面（前端无 /applications 路由、permissionMenu.ts 无映射）。
  资源目录却残留独立 module='application' 一族 6 码，与产品归属不符（与 0042
  管理单元 / 0045 编制管控 / 0047 待入职同源问题）。本次按 0047 同款先例处置：

    1. 重命名 2 个有真实负载的功能码，使其归属「候选人管理」模块、子模块「应聘记录」：
         recruit:application:list   → recruit:candidate:application:list   （应聘记录列表）
           真实负载：ApplicationViewSet(/api/v1/applications/) + GrabPoolViewSet(/api/v1/grab-pool/)
           + referral alias stubs；前端候选列表/详情靠它取投递次数与阶段信息。
         recruit:application:advance → recruit:candidate:application:advance （推进流程）
           注意：**改名保留而非停用** —— 兵哥清单（core.0041 第二批）明确把「推进流程」
           归在候选人管理策略卡下，停用会静默删卡；当前虽无前端调用点（仅 referral 501
           stub 复用），保留启用态与治理标记，未来流程按钮落地即插即用。
       🔴 命名遵循 V2 资源码规范（docs/DESIGN_资源编码规范.md）：
         - R4：第 1 段 == system_code（恒为 recruit）；
         - R2：第 2 段 == module 字段（candidate）。
         故新码为 recruit:candidate:application:*（与 recruit:candidate:offer:*/onboarding:* 同构）。
         码段保留 application（与后端 Application 模型 / /api/v1/applications/ 路由同源）。
    2. 停用（≠删除）4 条无任何端点守卫、无前端调用的死码（status=0 + [已停用] 前缀，
       保留可追溯；孤儿授权/模板引用一并清除）：
         recruit:application:menu:view（申请菜单——孤儿码，已被 资源下线候选清单_2026-10-18 标记）
         recruit:application:create / :edit / :reject（后端无 ViewSet 引用、前端无调用点）
    3. sub_module 置位「应聘记录」（与 RESOURCE_SUB_MODULES 真源一致；存量库由此迁移
       负责，全新库由 seed_v2_init 承担，双路径同 0047）。
    4. 动态策略：advance 行的 is_strategy_governed 标记随 update 原样保留（0041 置位
       不丢失）；改名后 module=candidate 直接入候选区，不再依赖
       STRATEGY_MODULE_RESOURCE_MODULES 的 'application' 桥接（该 key 暂留兼容历史）。

🔴 P0（沿用 0028/0036/0038/0042/0044/0047 教训）：三处存储点必须在同一事务内同步，否则静默失权：
    1. permission_resources.resource_code + module 字段
    2. role_permission.resource_code         （真实授权，漏改 = 授权全部失效）
    3. permission_templates.permission_codes （JSON 数组字面量，漏改 = 身份静默丢权）

设计要点（与 0036/0044/0047 同款）：
  - 幂等：旧码不存在（库已由新 seed 预置新码）时 RENAME 为 no-op；DISABLE 对缺失行
    亦 no-op；sub_module 置位为无条件 update，重复执行结果一致。
  - 顺序无关：先 migrate 后 seed、或先 seed 后 migrate，均不冲突。
  - 不改任何 endpoint 路径（/api/v1/applications/* 契约不变），仅权限码与守卫同步。
"""
from django.db import migrations

DISABLED_PREFIX = '[已停用] '


# 旧码 → (新码, 新中文名, 新类型, 新 module, 新 sub_module)
# 🔴 新码第 1 段恒为 system_code=recruit（R4），第 2 段 == module=candidate（R2）；
#    子模块 application（展示名「应聘记录」）落在第 3 段，动作段为末段
#    —— 与 recruit:candidate:offer:* 同构。
RENAME = {
    'recruit:application:list': ('recruit:candidate:application:list', '应聘记录列表', 'BUTTON', 'candidate', '应聘记录'),
    'recruit:application:advance': ('recruit:candidate:application:advance', '推进流程', 'BUTTON', 'candidate', '应聘记录'),
}

# 死码停用而非删除（status=0 + [已停用] 前缀，保留可追溯），并清掉其孤儿授权/模板引用：
# menu:view 为无页面孤儿码；create/edit/reject 后端无任何 ViewSet 守卫、前端无调用点。
DISABLE = [
    'recruit:application:menu:view',
    'recruit:application:create',
    'recruit:application:edit',
    'recruit:application:reject',
]


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
    # 死码的孤儿授权直接清除（对应功能无端点可消费，授权无意义）
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
                changed = True  # 丢弃死码的引用
            else:
                out.append(c)
        if changed:
            Template.objects.filter(pk=tpl.pk).update(permission_codes=out)


def _disable_resources(Resource):
    for code in DISABLE:
        rows = Resource.objects.filter(resource_code=code)
        if not rows.exists():
            continue  # 缺失行 → no-op（库已由新 seed 预置、无死码）
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
        f'[0048] 申请资源码重归属候选人管理：重命名 {len(RENAME)} 个 / '
        f'停用死码 {len(DISABLE)} 个（已同步 role_permission、permission_templates 与 sub_module）'
    )


def backward(apps, schema_editor):
    """反向：新码回退为旧 recruit:application:*（死码不恢复为启用，沿用停用态；
    sub_module 回置 NULL——旧码此前不在 0046 置位清单内，原初即空）。"""
    reverse = {v[0]: old for old, v in RENAME.items()}
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    old_names = {
        'recruit:application:list': '申请列表',
        'recruit:application:advance': '推进流程',
    }
    for new_code, old in reverse.items():
        if not Resource.objects.filter(resource_code=new_code).exists():
            continue
        if Resource.objects.filter(resource_code=old).exists():
            Resource.objects.filter(resource_code=new_code).delete()
        else:
            Resource.objects.filter(resource_code=new_code).update(
                resource_code=old,
                resource_name=old_names[old],
                module='application',
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
        ('core', '0047_rename_onboarding_resources_to_candidate'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
