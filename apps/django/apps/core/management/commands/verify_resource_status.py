"""巡检 / 修复 PermissionResource 的停用态一致性。

对应需求：将已停用资源明确标记为停用，并同步处理关联数据、清除误导性遗留状态。

扫描三类问题：
  1. 停用（status=0）资源缺少 `[已停用] ` 前缀 → 默认仅报告，`--fix` 自动补前缀。
  2. role_permission 残留对已停用资源的授权行（孤儿授权）→ 默认仅报告，
     `--purge-orphan-grants` 才会删除（默认关闭，属不可逆数据动作，需显式确认）。
  3. seed_v2_init.RESOURCES 含已知停用码（种子复活风险）→ 一律报告（阻断性，须从 seed 移除）。

用法：
  python manage.py verify_resource_status            # 仅报告
  python manage.py verify_resource_status --fix      # 报告 + 自动补前缀
  python manage.py verify_resource_status --fix --purge-orphan-grants  # 含删除孤儿授权
"""
import importlib

from django.core.management.base import BaseCommand
from django.db import transaction

DISABLED_PREFIX = '[已停用] '


class Command(BaseCommand):
    help = '巡检/修复 PermissionResource 停用态一致性（前缀 / 孤儿授权 / 种子复活）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true', default=False,
            help='自动为缺少前缀的停用资源补 [已停用] 前缀（默认仅报告）',
        )
        parser.add_argument(
            '--purge-orphan-grants', action='store_true', default=False,
            help='删除指向停用资源的 role_permission 孤儿授权行（默认关闭，不可逆）',
        )

    def handle(self, *args, **opts):
        from apps.core.models_permission_v2 import (
            PermissionResource,
            RolePermissionV2,
        )

        fix = opts['fix']
        purge = opts['purge_orphan_grants']

        # 已知停用码（0026 + 0029，单一事实源见 0033 迁移）
        m = importlib.import_module(
            'apps.core.migrations.0033_mark_disabled_resources'
        )
        known_disabled = set(m.KNOWN_DISABLED_CODES)

        # ---- 1. 停用资源前缀 ----
        disabled = list(PermissionResource.objects.filter(status=0))
        missing_prefix = [
            r for r in disabled
            if not r.resource_name.startswith(DISABLED_PREFIX)
        ]
        self.stdout.write(
            f'[1/3] 停用资源共 {len(disabled)} 条，其中缺失前缀 {len(missing_prefix)} 条'
        )
        if missing_prefix:
            if fix:
                with transaction.atomic():
                    for r in missing_prefix:
                        r.resource_name = DISABLED_PREFIX + r.resource_name
                        r.save(update_fields=['resource_name'])
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ 已补前缀 {len(missing_prefix)} 条')
                )
            else:
                for r in missing_prefix:
                    self.stdout.write(f'  - {r.resource_code} ({r.resource_name})')
                self.stdout.write(
                    self.style.WARNING('  未加 --fix，仅报告。')
                )

        # ---- 2. 孤儿授权（role_permission 指向停用资源） ----
        disabled_codes = {r.resource_code for r in disabled}
        orphan_grants = list(
            RolePermissionV2.objects.filter(resource_code__in=disabled_codes)
        )
        self.stdout.write(
            f'[2/3] role_permission 指向停用资源的孤儿授权共 {len(orphan_grants)} 条'
        )
        if orphan_grants:
            if purge:
                with transaction.atomic():
                    RolePermissionV2.objects.filter(
                        resource_code__in=disabled_codes,
                    ).delete()
                self.stdout.write(
                    self.style.SUCCESS(f'  ✓ 已删除 {len(orphan_grants)} 条孤儿授权')
                )
            else:
                seen = {}
                for g in orphan_grants:
                    seen.setdefault(g.role_code, []).append(g.resource_code)
                for role_code, codes in seen.items():
                    self.stdout.write(
                        f'  - 角色 {role_code}: {len(codes)} 个停用码授权'
                    )
                self.stdout.write(
                    self.style.WARNING(
                        '  默认保留（停用资源已通过 has_perm 拒绝授权，授权行惰性且可追溯）。'
                        ' 确认要清除请加 --purge-orphan-grants。'
                    )
                )

        # ---- 3. 种子复活风险 ----
        seed = importlib.import_module(
            'apps.core.management.commands.seed_v2_init'
        )
        seed_codes = {c for c, *_ in seed.RESOURCES}
        resurrected = known_disabled & seed_codes
        self.stdout.write(
            f'[3/3] seed 与已知停用码交集（复活风险）：{len(resurrected)} 条'
        )
        if resurrected:
            for c in sorted(resurrected):
                self.stdout.write(self.style.ERROR(f'  ! {c}'))
            self.stdout.write(
                self.style.ERROR(
                    '  ⛔ seed 含已停用码，重跑 seed 会强制启用并推翻 0026/0029 停用。'
                    ' 必须从 seed_v2_init.RESOURCES 移除这些码。'
                )
            )

        # ---- 汇总 ----
        problems = bool(missing_prefix and not fix) or bool(orphan_grants and not purge) or bool(resurrected)
        if resurrected:
            self.stdout.write(self.style.ERROR('结论：存在阻断性问题（种子复活风险），须立即处理。'))
        elif problems:
            self.stdout.write(self.style.WARNING('结论：存在可修复问题，复核后加 --fix / --purge-orphan-grants 处理。'))
        else:
            self.stdout.write(self.style.SUCCESS('结论：停用态一致性通过。'))
