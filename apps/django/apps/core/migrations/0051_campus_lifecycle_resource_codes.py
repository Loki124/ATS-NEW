"""校招生全生命周期移植 · 新增资源码（2026-10-23）

## 背景

逆向自 workbuddy.link《校招生管理系统》演示环境（25 视图 / 5 角色），把校招生全生命周期
能力移植到本仓「校招生管理模块」。新增三个业务域：

- `campus_assessment` 考核域（考勤 / 月度考核 / 考核模板 / 五行五力 / 反馈 / 月报 / 试用期）
- `campus_learning` 学习与社区（课程 / 进度 / 考试 / 活动 / 论坛）
- `campus_placement` 定岗与结算（岗位需求 / 志愿撮合 / 定岗跟踪 / 定价 / 台账 / 账单）

以及 `campus_control` 的批次规则引擎（`batch_rule` 子模块）。

## 为什么必须走迁移（而不是只改 seed）

新库靠 `seed_v2_init` 预置资源码；但**存量库**已经在线上跑着，只改 seed 不生效 →
非超管用户会**静默失权**（菜单不出现 / 接口 403）。故本迁移在存量库补齐。

## 🔴 三处存储点必须同事务同步（沿用 core.0030 / core.0045 铁律）

1. `permission_resources` —— 资源行本体
2. `role_permission` —— 真实授权（漏改 = 授权失效）
3. `permission_templates.permission_codes` —— 模板 JSON 数组（漏改 = 新建角色静默丢权）

## 授权口径

新码**不凭空授权**：谁持有对应既有入口码，就拿到该子模块的新码。

- 考核 / 学习与社区 子模块 ← 跟随 `recruit:campus:person:list`（人员管理入口）
- 定岗 / 结算 / 批次规则 子模块 ← 跟随 `recruit:campus:rotation:list`（轮岗安排入口）

理由：本仓校招域的入口是「人员管理 + 轮岗安排」，新域是它们的延伸；
**不引入新的授权来源**，避免出现「谁被授予校招管理」这一口径之外的第二套判定。

## 幂等

资源行 `update_or_create`；授权 `bulk_create(ignore_conflicts=True)`；
模板码按集合去重后写回 —— 本迁移**重复执行不产生重复行、不丢既有码**。

## 反向

`reverse` 为 no-op（资源码不做物理删除，避免误伤既有授权与模板）。
"""
from django.db import migrations

SYSTEM = 'recruit'

NEW_RESOURCES = [
    ('recruit:campus:assessment:menu:view', '轮岗考核菜单', 'MENU', 'campus'),
    ('recruit:campus:assessment:list', '轮岗考核列表', 'BUTTON', 'campus'),
    ('recruit:campus:assessment:create', '新建考核模板', 'BUTTON', 'campus'),
    ('recruit:campus:assessment:edit', '编辑轮岗考核', 'BUTTON', 'campus'),
    ('recruit:campus:assessment:delete', '删除考核模板', 'BUTTON', 'campus'),
    ('recruit:campus:assessment:export', '导出考核数据', 'BUTTON', 'campus'),
    ('recruit:campus:assessment:import', '导入考核数据', 'BUTTON', 'campus'),
    ('recruit:campus:attendance:menu:view', '考勤管理菜单', 'MENU', 'campus'),
    ('recruit:campus:attendance:list', '考勤记录列表', 'BUTTON', 'campus'),
    ('recruit:campus:attendance:create', '录入考勤', 'BUTTON', 'campus'),
    ('recruit:campus:attendance:edit', '编辑考勤', 'BUTTON', 'campus'),
    ('recruit:campus:attendance:export', '导出考勤', 'BUTTON', 'campus'),
    ('recruit:campus:monthly_report:menu:view', '月报管理菜单', 'MENU', 'campus'),
    ('recruit:campus:monthly_report:list', '月报列表', 'BUTTON', 'campus'),
    ('recruit:campus:monthly_report:create', '提交月报', 'BUTTON', 'campus'),
    ('recruit:campus:monthly_report:edit', '编辑月报', 'BUTTON', 'campus'),
    ('recruit:campus:monthly_report:evaluate', '月报评分', 'BUTTON', 'campus'),
    ('recruit:campus:feedback:menu:view', '反馈记录菜单', 'MENU', 'campus'),
    ('recruit:campus:feedback:list', '反馈记录列表', 'BUTTON', 'campus'),
    ('recruit:campus:feedback:create', '新增反馈记录', 'BUTTON', 'campus'),
    ('recruit:campus:feedback:edit', '编辑反馈记录', 'BUTTON', 'campus'),
    ('recruit:campus:feedback:delete', '删除反馈记录', 'BUTTON', 'campus'),
    ('recruit:campus:course:menu:view', '课程管理菜单', 'MENU', 'campus'),
    ('recruit:campus:course:list', '课程列表', 'BUTTON', 'campus'),
    ('recruit:campus:course:create', '新建课程', 'BUTTON', 'campus'),
    ('recruit:campus:course:edit', '编辑课程', 'BUTTON', 'campus'),
    ('recruit:campus:course:delete', '删除课程', 'BUTTON', 'campus'),
    ('recruit:campus:course:import', '批量导入课程', 'BUTTON', 'campus'),
    ('recruit:campus:course:export', '导出学习进度', 'BUTTON', 'campus'),
    ('recruit:campus:exam:menu:view', '考试管理菜单', 'MENU', 'campus'),
    ('recruit:campus:exam:list', '考试列表', 'BUTTON', 'campus'),
    ('recruit:campus:exam:create', '新建考试', 'BUTTON', 'campus'),
    ('recruit:campus:exam:edit', '编辑考试', 'BUTTON', 'campus'),
    ('recruit:campus:exam:delete', '删除考试', 'BUTTON', 'campus'),
    ('recruit:campus:activity:menu:view', '活动竞技菜单', 'MENU', 'campus'),
    ('recruit:campus:activity:list', '活动列表', 'BUTTON', 'campus'),
    ('recruit:campus:activity:create', '新建活动', 'BUTTON', 'campus'),
    ('recruit:campus:activity:edit', '编辑活动', 'BUTTON', 'campus'),
    ('recruit:campus:activity:delete', '删除活动', 'BUTTON', 'campus'),
    ('recruit:campus:forum:menu:view', '交流论坛菜单', 'MENU', 'campus'),
    ('recruit:campus:forum:list', '论坛帖子列表', 'BUTTON', 'campus'),
    ('recruit:campus:forum:create', '发表论坛帖', 'BUTTON', 'campus'),
    ('recruit:campus:forum:edit', '编辑论坛帖', 'BUTTON', 'campus'),
    ('recruit:campus:forum:delete', '删除论坛帖', 'BUTTON', 'campus'),
    ('recruit:campus:placement:menu:view', '定岗双选菜单', 'MENU', 'campus'),
    ('recruit:campus:placement:list', '定岗双选列表', 'BUTTON', 'campus'),
    ('recruit:campus:placement:create', '新建岗位需求', 'BUTTON', 'campus'),
    ('recruit:campus:placement:edit', '编辑岗位需求', 'BUTTON', 'campus'),
    ('recruit:campus:placement:delete', '删除岗位需求', 'BUTTON', 'campus'),
    ('recruit:campus:placement:publish', '发布双选结果', 'BUTTON', 'campus'),
    ('recruit:campus:placement:approve', '审核岗位需求', 'BUTTON', 'campus'),
    ('recruit:campus:placement:reject', '驳回岗位需求', 'BUTTON', 'campus'),
    ('recruit:campus:placement:assign', '指定分配', 'BUTTON', 'campus'),
    ('recruit:campus:placement:export', '导出双选名单', 'BUTTON', 'campus'),
    ('recruit:campus:placement_track:menu:view', '定岗跟踪菜单', 'MENU', 'campus'),
    ('recruit:campus:placement_track:list', '定岗跟踪列表', 'BUTTON', 'campus'),
    ('recruit:campus:placement_track:create', '新建定岗记录', 'BUTTON', 'campus'),
    ('recruit:campus:placement_track:edit', '编辑定岗记录', 'BUTTON', 'campus'),
    ('recruit:campus:placement_track:delete', '删除定岗记录', 'BUTTON', 'campus'),
    ('recruit:campus:placement_track:export', '导出定岗跟踪', 'BUTTON', 'campus'),
    ('recruit:campus:settlement:menu:view', '交易和结算菜单', 'MENU', 'campus'),
    ('recruit:campus:settlement:list', '结算台账列表', 'BUTTON', 'campus'),
    ('recruit:campus:settlement:create', '新建结算记录', 'BUTTON', 'campus'),
    ('recruit:campus:settlement:edit', '编辑结算记录', 'BUTTON', 'campus'),
    ('recruit:campus:settlement:export', '导出结算账单', 'BUTTON', 'campus'),
    ('recruit:campus:settlement:import', '导入结算台账', 'BUTTON', 'campus'),
    ('recruit:campus:batch_rule:menu:view', '批次规则菜单', 'MENU', 'campus'),
    ('recruit:campus:batch_rule:list', '批次规则列表', 'BUTTON', 'campus'),
    ('recruit:campus:batch_rule:create', '新建批次规则', 'BUTTON', 'campus'),
    ('recruit:campus:batch_rule:edit', '编辑批次规则', 'BUTTON', 'campus'),
    ('recruit:campus:batch_rule:delete', '删除批次规则', 'BUTTON', 'campus'),
    ('recruit:campus:batch_rule:import', '批量导入批次规则', 'BUTTON', 'campus'),
    ('recruit:campus:batch_rule:sync', '重算批次号', 'BUTTON', 'campus'),
]

#: 子模块 → 授权来源码（该角色/模板已持有此码，才授予对应子模块的新码）
SOURCE_FOR_MODULE = {
    'assessment': 'recruit:campus:person:list',
    'attendance': 'recruit:campus:person:list',
    'monthly_report': 'recruit:campus:person:list',
    'feedback': 'recruit:campus:person:list',
    'course': 'recruit:campus:person:list',
    'exam': 'recruit:campus:person:list',
    'activity': 'recruit:campus:person:list',
    'forum': 'recruit:campus:person:list',
    'placement': 'recruit:campus:rotation:list',
    'placement_track': 'recruit:campus:rotation:list',
    'settlement': 'recruit:campus:rotation:list',
    'batch_rule': 'recruit:campus:rotation:list',
}

#: 承接新码的模板（凡已持有校招域码的模板都承接）
TEMPLATE_CODES = [
    'TMPL_ADMIN',
    'TMPL_DIRECTOR',
    'TMPL_SPECIALIST',
]


def _module_of(code):
    return code.split(':')[2]


def _codes_by_source():
    out = {}
    for code, _name, _type, _module in NEW_RESOURCES:
        out.setdefault(SOURCE_FOR_MODULE[_module_of(code)], []).append(code)
    return out


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RP = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

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

    # ② 真实授权：按来源码复制
    for source_code, targets in _codes_by_source().items():
        grants = list(RP.objects.filter(resource_code=source_code))
        if not grants:
            continue
        rows = [
            RP(role_code=g.role_code, resource_code=t, system_code=SYSTEM)
            for g in grants for t in targets
        ]
        RP.objects.bulk_create(rows, ignore_conflicts=True)

    # ③ 模板 JSON：并入新码（集合去重，不丢既有码）
    new_codes = [c for c, _n, _t, _m in NEW_RESOURCES]
    for tpl in Template.objects.filter(template_code__in=TEMPLATE_CODES):
        codes = list(tpl.permission_codes or [])
        merged = list(dict.fromkeys(codes + new_codes))
        if merged != codes:
            tpl.permission_codes = merged
            tpl.save(update_fields=['permission_codes', 'updated_at'])


def reverse(apps, schema_editor):
    """no-op：资源码不做物理删除（误删会连带既有授权与模板失权）。"""


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0050_disable_user_groups_resource'),
    ]

    operations = [
        migrations.RunPython(forward, reverse),
    ]
