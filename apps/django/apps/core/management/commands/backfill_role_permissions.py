"""backfill_role_permissions — 按模板回填角色的功能权限（role_permission）。

为什么需要（G2/G4 前置）：
    `seed_v2_init` 只写 PermissionResource + PermissionTemplate，**不写 role_permission**；
    `init_demo_v2` 建 RoleV2 时也只写 template_code，不落 role_permission。
    于是除超管（is_super_admin bypass）外，所有用户的 `/me.permissions` 恒为 `[]`，
    `has_perm()` 一律 False（permission_check.py:28-29）。
    一旦把业务端点切到 V2Permission（缺口 G2）或前端按 permissions 过滤菜单（G4），
    这些用户会立刻 403 / 空菜单 —— 双重锁死。

本命令做什么：
    对「没有任何 role_permission 记录」的角色，按其 template_code 取模板的
    permission_codes 写入 role_permission（只写 PermissionResource 中真实存在的码）。
    幂等：已配置过的角色（有任意一行）一律跳过，不覆盖管理员在「身份管理」里的手工配置。

用法：
    python manage.py backfill_role_permissions --dry-run    # 预演
    python manage.py backfill_role_permissions              # 执行
    python manage.py backfill_role_permissions --role HR    # 只处理指定角色
    python manage.py backfill_role_permissions --grant-all  # 无模板的自定义角色也给全部码（谨慎）

未处理的情况会在输出里列出，需要管理员在「身份管理 → 功能权限」里手工勾选。
"""
from django.core.management.base import BaseCommand
from django.db import transaction

SYSTEM = 'recruit'

# 标准角色 → 模板的兜底映射 (与 init_demo_v2.ROLE_META 保持一致)。
# 背景: 现网/演示库里的 HR / HRBP / INTERVIEWER 等角色 template_code 为空
# (建角色时没写), 但语义明确。只靠 template_code 回填会让这些角色拿不到任何权限码,
# 而端点已按资源码校验 —— HR 这类挂着真实用户的角色会被整体锁死。
# 仅在 template_code 为空时使用; 显式配了模板的角色一律以模板为准。
ROLE_TEMPLATE_FALLBACK = {
    'SUPER_ADMIN': 'TMPL_ADMIN',
    'ADMIN': 'TMPL_ADMIN',
    'CHO': 'TMPL_DIRECTOR',
    'HR_DIRECTOR': 'TMPL_DIRECTOR',
    'AUDITOR': 'TMPL_DIRECTOR',
    'HRBP': 'TMPL_SPECIALIST',
    'HR': 'TMPL_SPECIALIST',
    'HIRING_MANAGER': 'TMPL_SPECIALIST',
    'INTERVIEWER': 'TMPL_INTERVIEWER',
    'REFERRER': 'TMPL_INTERVIEWER',
}


class Command(BaseCommand):
    help = '按 PermissionTemplate 回填 RoleV2 的 role_permission（补 seed/init_demo 遗漏的功能权限落库）'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='只报告不写库')
        parser.add_argument('--role', dest='role_code', default=None, help='只处理指定 role_code')
        parser.add_argument(
            '--grant-all', action='store_true',
            help='无模板且非系统角色的自定义角色，也授予全部启用中的资源码（谨慎）',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        from apps.core.models_permission_v2 import (
            PermissionResource,
            PermissionTemplate,
            RolePermissionV2,
            RoleV2,
        )

        dry_run = options['dry_run']
        only_role = options.get('role_code')
        grant_all = options['grant_all']

        valid_codes = set(
            PermissionResource.objects.filter(system_code=SYSTEM, status=1)
            .values_list('resource_code', flat=True)
        )
        templates = {
            t.template_code: list(t.permission_codes or [])
            for t in PermissionTemplate.objects.filter(system_code=SYSTEM, status=1)
        }
        all_codes = sorted(valid_codes)

        roles = RoleV2.objects.filter(system_code=SYSTEM, status=1).order_by('role_code')
        if only_role:
            roles = roles.filter(role_code=only_role)

        skipped_configured = skipped_no_codes = granted_roles = 0
        missing_template: list[str] = []
        unknown_codes: set[str] = set()
        created_rows = 0

        for role in roles:
            has_rows = RolePermissionV2.objects.filter(
                role_code=role.role_code, system_code=SYSTEM
            ).exists()
            if has_rows:
                skipped_configured += 1
                continue

            tpl_code = (role.template_code or '').strip() or ROLE_TEMPLATE_FALLBACK.get(
                role.role_code, ''
            )
            inferred = not (role.template_code or '').strip()
            if role.role_code == 'SUPER_ADMIN':
                codes = all_codes
            elif tpl_code and tpl_code in templates:
                codes = [c for c in templates[tpl_code] if c in valid_codes]
                unknown_codes |= {c for c in templates[tpl_code] if c not in valid_codes}
            elif grant_all:
                codes = all_codes
            else:
                missing_template.append(f'{role.role_code}(template={tpl_code or "无"})')
                skipped_no_codes += 1
                continue

            if not codes:
                missing_template.append(f'{role.role_code}(模板 {tpl_code} 无有效资源码)')
                skipped_no_codes += 1
                continue

            suffix = f'（模板 {tpl_code}{"，按标准角色推断" if inferred else ""}）'
            if dry_run:
                self.stdout.write(f'[dry-run] {role.role_code}: 将写入 {len(codes)} 个资源码{suffix}')
            else:
                RolePermissionV2.objects.bulk_create([
                    RolePermissionV2(
                        role_code=role.role_code, resource_code=c, system_code=SYSTEM
                    )
                    for c in codes
                ], ignore_conflicts=True)
                created_rows += len(codes)
                self.stdout.write(f'✓ {role.role_code}: 写入 {len(codes)} 个资源码{suffix}')
            granted_roles += 1

        verb = '待回填' if dry_run else '已回填'
        self.stdout.write(self.style.SUCCESS(
            f'角色总数 {roles.count()} / {verb} {granted_roles} 个'
            f'{"，写入 " + str(created_rows) + " 行" if not dry_run else ""}'
            f' / 已配置跳过 {skipped_configured} / 无可用权限码跳过 {skipped_no_codes}'
        ))

        if unknown_codes:
            self.stdout.write(self.style.WARNING(
                f'模板引用了 PermissionResource 中不存在的码（已在回填时跳过，'
                f'建议补进 seed_v2_init.RESOURCES）: {sorted(unknown_codes)}'
            ))
        if missing_template:
            self.stdout.write(self.style.WARNING(
                '以下角色未回填，需在「身份管理 → 功能权限」手工勾选，'
                '或加 --grant-all 一次给全：\n  - ' + '\n  - '.join(missing_template)
            ))
