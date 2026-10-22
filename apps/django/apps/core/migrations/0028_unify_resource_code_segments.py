"""统一资源码分段命名风格：连字符 → 下划线 (2026-10-18)

背景见 docs/DESIGN_资源编码规范.md §2/§6。

实测存量存在两套分段命名风格并存：
  - 第 3 段（下划线族）: job_title / job_level / mgmt_unit / user_role / talent_pool / user_app_data_scope
  - 第 3 段（连字符族）: company-brand / field-acl / rule-engine / data-dashboard …共 29 个段值、98 条码

第 2 段因护栏 R2（段 2 必须 == module 字段值）恒为下划线族（module 值天生是 Python
标识符），故连字符只可能出现在第 3 段。本迁移把第 3 段的 29 个连字符段值统一改为
下划线，**不改动第 1/2/4…段**，因此 R2 规则与 module 字段值不受任何影响。

🔴 P0：三处存储点必须在同一个事务里同步改，否则静默失权
  1. permission_resources.resource_code   （资源定义本体）
  2. role_permission.resource_code         （868 行真实授权，漏改 = 授权全部失效）
  3. permission_templates.permission_codes （JSON 数组存码字面量，漏改 = 身份静默丢权）

命名收敛为 snake_case 后，「同名不同写法」这类僵尸码从根上不可能再产生。
"""

from django.db import migrations

# 段 3 连字符 → 下划线。仅覆盖实测存在的段值，不做正则通配，
# 避免误伤末段动作词或未来新增的合法连字符。
#
# 🔴 完整性要求：这张表必须覆盖**库内全部**含连字符的段值（含仅存于
#    permission_resources、seed 里已不存在的下线残留码），否则迁移后仍残留连字符码，
#    护栏 R7 会在真实库上失败。0028 首版漏了 data-permission / user-management
#    这两个段值 —— 它们只属于 0029 要停用的孤儿资源，不属于 seed，但确实在库里。
SEG_RENAME = {
    'application-form': 'application_form',
    'approval-flow': 'approval_flow',
    'campus-control': 'campus_control',
    'candidate-dynamic-fields': 'candidate_dynamic_fields',
    'candidate-info-table': 'candidate_info_table',
    'code-tables': 'code_tables',
    'company-address': 'company_address',
    'company-brand': 'company_brand',
    'company-library': 'company_library',
    'company-meeting-rooms': 'company_meeting_rooms',
    'company-resume-mailbox': 'company_resume_mailbox',
    # ↓ 下线残留码的段值：seed 已无，0029 会停用，但改名仍需覆盖以满足 R7
    'data-dashboard': 'data_dashboard',
    'data-permission': 'data_permission',
    'demand-config': 'demand_config',
    'demand-dynamic-fields': 'demand_dynamic_fields',
    'duplicate-candidate': 'duplicate_candidate',
    'dynamic-fields': 'dynamic_fields',
    'field-acl': 'field_acl',
    'interview-management': 'interview_management',
    'offer-management': 'offer_management',
    # ↓ 校招操作日志按钮原本写成 operation-log（段 3 连字符），与 0028 统一风格脱节。
    #   补进映射：库内若残留 operation-log 段值，0028 自检与改名逻辑即可覆盖，
    #   避免「新库 seed → 0028 自检 RuntimeError」的潜在阻塞。
    'operation-log': 'operation_log',
    'position-dynamic-fields': 'position_dynamic_fields',
    'position-info': 'position_info',
    'recruitment-process': 'recruitment_process',
    'recruitment-round': 'recruitment_round',
    'recruitment-stage': 'recruitment_stage',
    'rule-engine': 'rule_engine',
    'school-library': 'school_library',
    'scraped-resumes': 'scraped_resumes',
    'standard-resume': 'standard_resume',
    'user-groups': 'user_groups',
    'user-management': 'user_management',
}


def rename_code(code):
    """把任意位置的连字符段改下划线（不止第 3 段：下线残留码可能出现在任意层）。"""
    if not code or not isinstance(code, str):
        return None
    parts = code.split(':')
    changed = False
    for i, p in enumerate(parts):
        new = SEG_RENAME.get(p)
        if new:
            parts[i] = new
            changed = True
    return ':'.join(parts) if changed else None


def forward(apps, schema_editor):
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    # --- 0. 自检：段映射必须覆盖库内全部含连字符的段值 ---
    # 不做这一步的后果实测过：首版映射表漏了 data-permission / user-management，
    # 迁移跑完库里仍残留 10 条连字符码，护栏 R7 在真实库上直接失败。
    library_segments = set()
    for code in Resource.objects.values_list('resource_code', flat=True):
        library_segments.update(s for s in (code or '').split(':') if '-' in s)
    uncovered = library_segments - set(SEG_RENAME)
    if uncovered:
        raise RuntimeError(
            f'[0028] SEG_RENAME 未覆盖库内连字符段值 {sorted(uncovered)}，'
            f'请补齐后重跑；否则迁移后仍残留连字符码，R7 护栏会失败'
        )

    # --- 1. 资源定义本体（unique 约束，必须逐条改，批量 UPDATE 会撞 1062）---
    resource_map = {}
    for code in Resource.objects.values_list('resource_code', flat=True):
        new = rename_code(code)
        if new:
            resource_map[code] = new
    for old, new in resource_map.items():
        if Resource.objects.filter(resource_code=new).exists():
            raise RuntimeError(f'[0028] 目标码已存在，禁止继续：{old} → {new}')
        Resource.objects.filter(resource_code=old).update(resource_code=new)

    # --- 2. 真实授权（uk: role_code + resource_code）---
    renamed_auth = 0
    for rp in RolePermission.objects.all().iterator():
        new = rename_code(rp.resource_code)
        if not new:
            continue
        dup = RolePermission.objects.filter(
            role_code=rp.role_code, resource_code=new,
        ).exclude(pk=rp.pk).exists()
        if dup:
            # 授权侧无冲突可容忍的语义：合并到既有行，避免撞唯一约束
            RolePermission.objects.filter(pk=rp.pk).delete()
        else:
            RolePermission.objects.filter(pk=rp.pk).update(resource_code=new)
        renamed_auth += 1

    # --- 3. 模板 JSON 数组（字面量，必须逐条解析改写）---
    renamed_tpl = 0
    for tpl in Template.objects.all().iterator():
        codes = tpl.permission_codes or []
        if not isinstance(codes, list):
            continue
        changed = False
        out = []
        for c in codes:
            new = rename_code(c)
            if new and new not in out:
                out.append(new)
                changed = True
            elif new:
                # 改名后与已有码撞车 → 去重，避免模板内出现重复条目
                changed = True
            else:
                out.append(c)
        if changed:
            Template.objects.filter(pk=tpl.pk).update(permission_codes=out)
            renamed_tpl += 1

    print(
        f'[0028] 资源码分段统一：资源 {len(resource_map)} 条 / '
        f'授权 {renamed_auth} 行 / 模板 {renamed_tpl} 个'
    )


def backward(apps, schema_editor):
    reverse = {v: k for k, v in SEG_RENAME.items()}
    Resource = apps.get_model('core', 'PermissionResource')
    RolePermission = apps.get_model('core', 'RolePermissionV2')
    Template = apps.get_model('core', 'PermissionTemplate')

    def revert(code):
        if not code or not isinstance(code, str):
            return None
        parts = code.split(':')
        changed = False
        for i, p in enumerate(parts):
            old = reverse.get(p)
            if old:
                parts[i] = old
                changed = True
        return ':'.join(parts) if changed else None

    for code in list(Resource.objects.values_list('resource_code', flat=True)):
        new = revert(code)
        if new:
            Resource.objects.filter(resource_code=code).update(resource_code=new)

    for rp in RolePermission.objects.all().iterator():
        new = revert(rp.resource_code)
        if not new:
            continue
        if RolePermission.objects.filter(
            role_code=rp.role_code, resource_code=new,
        ).exclude(pk=rp.pk).exists():
            RolePermission.objects.filter(pk=rp.pk).delete()
        else:
            RolePermission.objects.filter(pk=rp.pk).update(resource_code=new)

    for tpl in Template.objects.all().iterator():
        codes = tpl.permission_codes or []
        if not isinstance(codes, list):
            continue
        out, changed = [], False
        for c in codes:
            new = revert(c)
            if new and new not in out:
                out.append(new)
                changed = True
            elif new:
                changed = True
            else:
                out.append(c)
        if changed:
            Template.objects.filter(pk=tpl.pk).update(permission_codes=out)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0027_fix_module_field'),
    ]

    operations = [
        migrations.RunPython(forward, backward),
    ]
