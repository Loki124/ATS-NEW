"""校招生全生命周期 · 补登 attendance / monthly_report 的 `:delete` 资源码（2026-10-24）

## 背景

core.0051 给 `attendance` / `monthly_report` 两个子模块登记了
`list/create/edit[/evaluate]/export`，**独缺 `:delete`**。

而运行时 `apps/core/permissions_v2.py` 的默认动作派生是
`destroy → :delete`（模块级 ViewSet 未显式改派时的兜底路径）。
未登记的码会被 **fail-closed 守卫拒成 403** —— 也就是说：
契约 §2.2 要求提供的删除端点，只要走到默认派生就必然被拒。

`apps/campus_assessment/views.py` 当时把这两个子模块的 destroy **显式改派**到
已登记的 `:edit`，功能因此没坏，但**偏离了契约的默认映射**（别人的 `:edit`
被拿来当删除权限用，授权语义被稀释）。

## 修法：按契约来，不继续绕

把 `:delete` 码补登进资源表，让 destroy **回到默认派生**（视图层改派由并行任务完成）。

## 🔴 三处存储点必须同事务同步（沿用 core.0030 / 0045 / 0051 铁律）

1. `permission_resources` —— 资源行本体
2. `role_permission` —— 真实授权（漏改 = 授权失效）
3. `permission_templates.permission_codes` —— 模板 JSON 数组（漏改 = 新建角色静默丢权）

## 授权口径

新码**不凭空授权**：谁持有 `recruit:campus:person:list`（人员管理入口），
就拿到这两个子模块的新码 —— 与 core.0051 对 `attendance` / `monthly_report`
两个子模块的授权来源保持一致，不引入第二套判定口径。

## 幂等

资源行 `update_or_create`；授权 `bulk_create(ignore_conflicts=True)`
（`role_permission` 上有 `uk_role_resource` 唯一约束，必须 ignore_conflicts）；
模板码按集合去重后写回 —— 本迁移**重复执行不产生重复行、不丢既有码**。

## 反向

`reverse` 为 no-op（资源码不做物理删除，避免误伤既有授权与模板）。
"""
from django.db import migrations

SYSTEM = 'recruit'

#: 本次补登的资源码：(code, name, type, module)
NEW_RESOURCES = [
    ('recruit:campus:attendance:delete', '删除考勤记录', 'BUTTON', 'campus'),
    ('recruit:campus:monthly_report:delete', '删除月报', 'BUTTON', 'campus'),
]

#: 授权来源码（与 core.0051 对这两个子模块的口径一致）
SOURCE_CODE = 'recruit:campus:person:list'

#: 承接新码的模板（凡已持有校招域码的模板都承接，与 core.0051 同款）
TEMPLATE_CODES = [
    'TMPL_ADMIN',
    'TMPL_DIRECTOR',
    'TMPL_SPECIALIST',
]


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RP = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    new_codes = [c for c, _n, _t, _m in NEW_RESOURCES]

    # ① 资源行本体
    for code, name, rtype, module in NEW_RESOURCES:
        Resource.objects.update_or_create(
            resource_code=code,
            defaults={
                'resource_name': name,
                'resource_type': rtype,
                'module': module,
                'system_code': SYSTEM,
                'status': 1,
            },
        )

    # ② 真实授权：跟随来源码的持有者
    grants = list(RP.objects.filter(resource_code=SOURCE_CODE))
    if grants:
        rows = [
            RP(role_code=g.role_code, resource_code=c, system_code=SYSTEM)
            for g in grants for c in new_codes
        ]
        RP.objects.bulk_create(rows, ignore_conflicts=True)

    # ③ 模板 JSON：并入新码（集合去重，不丢既有码）
    for tpl in Template.objects.filter(template_code__in=TEMPLATE_CODES):
        codes = list(tpl.permission_codes or [])
        merged = list(dict.fromkeys(codes + new_codes))
        if merged != codes:
            tpl.permission_codes = merged
            tpl.save(update_fields=['permission_codes', 'updated_at'])

    print(
        f'[0052] 补登资源码 {len(new_codes)} 条：{new_codes}'
        f'（已同步 role_permission 与 permission_templates，授权来源 {SOURCE_CODE}）'
    )


def reverse(apps, schema_editor):
    """no-op：资源码不做物理删除（误删会连带既有授权与模板失权）。"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_campus_lifecycle_resource_codes'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
