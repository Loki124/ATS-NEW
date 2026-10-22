"""校招资源码拆分 + 资源名对齐 + 停用码前缀化（2026-10-18）。

本迁移是数据迁移（无 schema 变更），`makemigrations --check` 必须仍返回 clean。

## 一、背景与裁决（详见 docs/ARCH_校招资源码拆分与资源名对齐.md §11）

### 1. 校招三功能拆分
`recruit:settings:campus_control:*` 此前一码覆盖三个界面入口（校招管控 / 校园大使 /
宣讲会）。按兵哥裁决拆分为三个独立码族：
  - `campus_control`（保留原码，零改名）
  - `campus_ambassador`（新增 4 条）
  - `campus_session`（新增 4 条）
历史授权 1→3 复制展开（不删任何一行），保证零静默失权、零新增越权。

### 2. rule_engine 拆成两个码（兵哥裁决 R2，否决架构师「不拆」建议）
实测后端接线：`/settings/rule-engine` 守 `rule_engine:*`；`/settings/resume-parser-engine`
只调 `apps/add_candidate/views.py:477 ResumeParserConfigView`，其原本守
`standard_resume:*`。故拆码 = 新增 `resume_parser_engine:*` 码族（3 条），
并把 `ResumeParserConfigView` 的守卫从 `standard_resume` 改指 `resume_parser_engine`
（见 T04），同时把 `standard_resume:*` 的授权 1:1 复制给 `resume_parser_engine`。

### 3. 校招管控迁主菜单（兵哥裁决 R3）
资源码 `campus_control:*` 不变，仅前端菜单入口从「设置页」迁移到「校园招聘」分组
（见 T05）。本迁移不触碰前端。

### 4. 资源名对齐（15 条，均幂等、不含 status=0）
code_tables 全族 6 条「码表*」→「静态数据*」；rule_engine:menu:view
「统一规则引擎菜单」→「规则引擎菜单」；campus_control:menu:view
「校招管控菜单」→「校招管控」；campus:resource:{create,edit,delete}
「*直播间」→「*轮岗资源」；metrics:list「指标列表」→「指标管理」。

### 5. mou 整族停用（5 条）+ 停用码前缀化（幂等）
`mou` 是前端零消费的 MOU 协议 stub，整族停用；所有 `status=0` 资源名加
`[已停用] ` 前缀（幂等，已带前缀的不叠加）。seed 真源（0026/0029/mou 共 19 条）
已在 seed_v2_init 中删除，本迁移按库内 `status=0` 动态集合打前缀，覆盖全部停用码。

🔴 设计铁律：三处存储点（permission_resources / role_permission /
permission_templates）**必须在同一事务内同步**，任一断言失败整体回滚。
"""
from django.db import migrations
from django.db.models import CharField, F, Value
from django.db.models.functions import Concat

SYSTEM = 'recruit'
DISABLED_PREFIX = '[已停用] '

# 校招管控 4 条原码
CC_CODES = [
    'recruit:settings:campus_control:menu:view',
    'recruit:settings:campus_control:list',
    'recruit:settings:campus_control:edit',
    'recruit:settings:campus_control:delete',
]
CAMPUS_NEW_FAMILIES = ['campus_ambassador', 'campus_session']

# 标准简历 3 条原码（其守卫被 resume_parser_engine 接管）
SR_CODES = [
    'recruit:settings:standard_resume:menu:view',
    'recruit:settings:standard_resume:list',
    'recruit:settings:standard_resume:edit',
]
RPE_FAMILY = 'resume_parser_engine'

# 新增 11 条资源（code, name, type, module）
NEW_RESOURCES = [
    ('recruit:settings:campus_ambassador:menu:view', '校园大使菜单', 'MENU', 'settings'),
    ('recruit:settings:campus_ambassador:list', '校园大使列表', 'BUTTON', 'settings'),
    ('recruit:settings:campus_ambassador:edit', '编辑校园大使', 'BUTTON', 'settings'),
    ('recruit:settings:campus_ambassador:delete', '删除校园大使', 'BUTTON', 'settings'),
    ('recruit:settings:campus_session:menu:view', '宣讲会菜单', 'MENU', 'settings'),
    ('recruit:settings:campus_session:list', '宣讲会列表', 'BUTTON', 'settings'),
    ('recruit:settings:campus_session:edit', '编辑宣讲会', 'BUTTON', 'settings'),
    ('recruit:settings:campus_session:delete', '删除宣讲会', 'BUTTON', 'settings'),
    ('recruit:settings:resume_parser_engine:menu:view', '简历解析引擎菜单', 'MENU', 'settings'),
    ('recruit:settings:resume_parser_engine:list', '简历解析引擎列表', 'BUTTON', 'settings'),
    ('recruit:settings:resume_parser_engine:edit', '编辑简历解析引擎', 'BUTTON', 'settings'),
]
NEW_CODES_ALL = [r[0] for r in NEW_RESOURCES]
CAMPUS_NEW_CODES = [
    c.replace('campus_control', fam)
    for fam in CAMPUS_NEW_FAMILIES for c in CC_CODES
]
RPE_NEW_CODES = [c.replace('standard_resume', RPE_FAMILY) for c in SR_CODES]

# 资源名对齐（15 条，幂等：仅当 status=1 且当前名 != 新名才改）
RENAME_MAP = {
    'recruit:settings:code_tables:menu:view': '静态数据菜单',
    'recruit:settings:code_tables:list': '静态数据列表',
    'recruit:settings:code_tables:create': '新增静态数据',
    'recruit:settings:code_tables:edit': '编辑静态数据',
    'recruit:settings:code_tables:delete': '删除静态数据',
    'recruit:settings:code_tables:export': '导出静态数据',
    'recruit:settings:rule_engine:menu:view': '规则引擎菜单',
    'recruit:settings:campus_control:menu:view': '校招管控',
    'recruit:campus:resource:create': '新建轮岗资源',
    'recruit:campus:resource:edit': '编辑轮岗资源',
    'recruit:campus:resource:delete': '删除轮岗资源',
    'recruit:settings:metrics:list': '指标管理',
}
# backward 反向映射（新名 → 旧名）
RENAME_REVERSE = {
    'recruit:settings:code_tables:menu:view': '码表库菜单',
    'recruit:settings:code_tables:list': '码表列表',
    'recruit:settings:code_tables:create': '新增码表',
    'recruit:settings:code_tables:edit': '编辑码表',
    'recruit:settings:code_tables:delete': '删除码表',
    'recruit:settings:code_tables:export': '导出码表',
    'recruit:settings:rule_engine:menu:view': '统一规则引擎菜单',
    'recruit:settings:campus_control:menu:view': '校招管控菜单',
    'recruit:campus:resource:create': '新建直播间',
    'recruit:campus:resource:edit': '编辑直播间',
    'recruit:campus:resource:delete': '删除直播间',
    'recruit:settings:metrics:list': '指标列表',
}

# mou 整族停用（5 条）
MOU_CODES = [
    'recruit:mou:menu:view',
    'recruit:mou:list',
    'recruit:mou:create',
    'recruit:mou:edit',
    'recruit:mou:approve',
]


def _copy_grants(apps, source_codes, target_family, old_segment):
    """把 source_codes 的 role_permission 授权 1:1 复制给 target_family（替换段名）。

    幂等：bulk_create 用 ignore_conflicts 绕过 uk_role_resource。
    """
    RP = apps.get_model('core', 'RolePermissionV2')
    created = 0
    for old in source_codes:
        new = old.replace(old_segment, target_family)
        rows = list(RP.objects.filter(resource_code=old))
        if not rows:
            continue
        new_rows = [
            RP(role_code=r.role_code, resource_code=new, system_code=SYSTEM)
            for r in rows
        ]
        RP.objects.bulk_create(new_rows, ignore_conflicts=True)
        created += len(new_rows)
    return created


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RP = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    # 快照历史授权行数（A3 / A4 基准；空库天然为 0，属正常）
    cc_before = RP.objects.filter(resource_code__in=CC_CODES).count()
    # noqa 说明: sr_before 是 A3/A4 的迁移前基线快照，与 cc_before 成对留存。
    # 迁移已应用, 保留变量不删（改了会让历史迁移与当初的执行轨迹不一致）;
    # ruff F841 只因它在本迁移里未被读取。卡 A6。
    sr_before = RP.objects.filter(resource_code__in=SR_CODES).count()  # noqa: F841

    # ① 新建 11 条资源（幂等 update_or_create）
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

    # ② 校招管控授权 1→3 复制展开
    campus_created = 0
    for fam in CAMPUS_NEW_FAMILIES:
        campus_created += _copy_grants(apps, CC_CODES, fam, 'campus_control')

    # ③ standard_resume → resume_parser_engine 1:1 复制
    rpe_created = _copy_grants(apps, SR_CODES, RPE_FAMILY, 'standard_resume')

    # ⑤ 停用 mou 整族（必须在 ⑥ 之前：前缀依赖 status=0）
    mou_hit = Resource.objects.filter(
        resource_code__in=MOU_CODES, status=1
    ).update(status=0)

    # ⑥ 停用码按 status=0 动态集合打前缀（幂等，已带前缀的不叠加）
    prefix_hit = Resource.objects.filter(status=0).exclude(
        resource_name__startswith=DISABLED_PREFIX
    ).update(
        resource_name=Concat(
            Value(DISABLED_PREFIX), F('resource_name'),
            output_field=CharField(max_length=64),
        )
    )

    # ④ 模板 JSON 改写：展开 campus（4→12）+ 新增 resume_parser_engine（3），
    #    并剥离任何停用码/悬空码（R11：模板不得引用停用或不存在的码）。
    #    🔴 必须在 ⑤⑥ 之后执行：此时 mou 已停用，按 active_codes 过滤才能把它
    #    从模板中剔除（否则模板会引用到一个已停用的资源码，造成授权泄漏/悬空）。
    active_codes = set(
        Resource.objects.filter(status=1).values_list('resource_code', flat=True)
    )
    tpl_changed = 0
    for t in Template.objects.all():
        codes = list(t.permission_codes or [])
        changed = False
        if any(c in codes for c in CC_CODES):
            for nc in CAMPUS_NEW_CODES:
                if nc not in codes:
                    codes.append(nc)
                    changed = True
        if any(c in codes for c in SR_CODES):
            for nc in RPE_NEW_CODES:
                if nc not in codes:
                    codes.append(nc)
                    changed = True
        filtered = [c for c in codes if c in active_codes]
        if len(filtered) != len(codes):
            changed = True
        # 去重保序
        seen = set()
        deduped = []
        for c in filtered:
            if c not in seen:
                seen.add(c)
                deduped.append(c)
        if changed:
            t.permission_codes = deduped
            t.save(update_fields=['permission_codes'])
            tpl_changed += 1

    # ⑦ 在用资源改名（15 条，幂等：仅 status=1 且当前名 != 新名）
    rename_hit = 0
    for code, new_name in RENAME_MAP.items():
        n = Resource.objects.filter(
            resource_code=code, status=1
        ).exclude(resource_name=new_name).update(resource_name=new_name)
        rename_hit += n

    # ---------- 自检断言 ----------
    # A1（软）：campus_control 基线若存在必须启用态；空库/未 seed 属正常
    cc_missing = [
        c for c in CC_CODES
        if not Resource.objects.filter(resource_code=c, status=1).exists()
    ]
    if cc_missing:
        print(f'[0030] 警告：campus_control 基线缺失 {cc_missing}（空库/未 seed 属正常）')

    # A2（硬）：11 条新码必须存在且启用
    for code in NEW_CODES_ALL:
        if not Resource.objects.filter(resource_code=code, status=1).exists():
            raise RuntimeError(f'[0030] A2 失败：新码缺失或停用 {code}')

    # A3（硬）：校招管控授权行数未被删除
    cc_after = RP.objects.filter(resource_code__in=CC_CODES).count()
    if cc_after != cc_before:
        raise RuntimeError(f'[0030] A3 失败：campus_control 授权行数 {cc_before}→{cc_after}')

    # A4（硬）：每个新码授权利 == 对应旧码授权利
    for fam in CAMPUS_NEW_FAMILIES:
        for old in CC_CODES:
            new = old.replace('campus_control', fam)
            old_n = RP.objects.filter(resource_code=old).count()
            new_n = RP.objects.filter(resource_code=new).count()
            if new_n != old_n:
                raise RuntimeError(
                    f'[0030] A4 失败：{new} 授权 {new_n} != {old} 授权 {old_n}'
                )
    for old in SR_CODES:
        new = old.replace('standard_resume', RPE_FAMILY)
        old_n = RP.objects.filter(resource_code=old).count()
        new_n = RP.objects.filter(resource_code=new).count()
        if new_n != old_n:
            raise RuntimeError(
                f'[0030] A4 失败：{new} 授权 {new_n} != {old} 授权 {old_n}'
            )

    # A5（硬）：模板不得引用悬空码（库内不存在的码）
    valid = set(Resource.objects.values_list('resource_code', flat=True))
    for t in Template.objects.all():
        for c in (t.permission_codes or []):
            if c not in valid:
                raise RuntimeError(
                    f'[0030] A5 失败：模板 {t.template_code} 引用悬空码 {c}'
                )

    # A6（硬）：每个 MENU 前缀至多一条 MENU（防一前缀两条 MENU 打乱权限树）
    families = [
        ':'.join(c.split(':')[:4])
        for c in Resource.objects.filter(resource_type='MENU').values_list(
            'resource_code', flat=True
        )
    ]
    if len(families) != len(set(families)):
        dup = {f for f in families if families.count(f) > 1}
        raise RuntimeError(f'[0030] A6 失败：MENU 前缀重复 {dup}')

    # A7（硬）：resume_parser_engine 新码存在且授权利 == standard_resume（A4 已覆盖，此处再确认新码存在）
    for code in RPE_NEW_CODES:
        if not Resource.objects.filter(resource_code=code, status=1).exists():
            raise RuntimeError(f'[0030] A7 失败：resume_parser_engine 新码缺失 {code}')

    # W1 / W2：计数打印
    print(
        f'[0030] 新建资源 0（update_or_create 幂等）| 校招授权复制 +{campus_created} '
        f'| resume_parser_engine 授权复制 +{rpe_created} | 模板改写 {tpl_changed} 个'
    )
    print(
        f'[0030] 停用 mou {mou_hit} 条 | 停用码前缀 {prefix_hit} 条 | 在用改名 {rename_hit} 条'
    )
    print(
        f'[0030] 当前启用资源 {Resource.objects.filter(status=1).count()} '
        f'/ 停用资源 {Resource.objects.filter(status=0).count()}'
    )


def backward(apps, schema_editor):
    """应急回滚（非常规路径）。

    ① 删除 11 条新码的授权与资源；② 模板移除新码；③ 恢复 15 条改名；
    ④ 解除所有 `[已停用] ` 前缀；⑤ mou 重新启用。
    注意：若 forward 后管理员手动改过名称，回滚会一并丢弃，属可接受（应急路径）。
    """
    Resource = apps.get_model('core', 'PermissionResource')
    RP = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    # ① 删除新码授权与资源
    RP.objects.filter(resource_code__in=NEW_CODES_ALL).delete()
    Resource.objects.filter(resource_code__in=NEW_CODES_ALL).delete()

    # ② 模板移除新码
    for t in Template.objects.all():
        codes = list(t.permission_codes or [])
        filtered = [c for c in codes if c not in NEW_CODES_ALL]
        if len(filtered) != len(codes):
            t.permission_codes = filtered
            t.save(update_fields=['permission_codes'])

    # ③ 恢复 15 条改名
    for code, old_name in RENAME_REVERSE.items():
        Resource.objects.filter(resource_code=code, status=1).update(
            resource_name=old_name
        )

    # ④ 解除所有 `[已停用] ` 前缀（反向 forward 的前缀化）
    from django.db.models.functions import Replace
    Resource.objects.filter(
        resource_name__startswith=DISABLED_PREFIX
    ).update(
        resource_name=Replace(
            'resource_name', Value(DISABLED_PREFIX), Value(''),
            output_field=CharField(max_length=64),
        )
    )

    # ⑤ mou 重新启用（解除停用）
    Resource.objects.filter(resource_code__in=MOU_CODES).update(status=1)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_disable_zombie_resources'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
