"""检查 automation 规则与统一规则引擎镜像的一致性（Phase 2）。

用途：
- 灰度期验证双写（RULE_ENGINE_DOUBLE_WRITE）是否把所有 automation 规则正确镜像；
- 发现「缺失镜像 / 字段漂移 / 应软删未软删」三类不一致。

用法：
    python manage.py check_rule_engine_consistency
    python manage.py check_rule_engine_consistency --fix     # 重新同步以消除不一致

退出码：发现不一致且非 --fix 时为 1，否则 0（便于 CI 断言）。
"""
from django.core.management.base import BaseCommand

from apps.rule_engine.bridge import (
    AUTOMATION_LEGACY_MODEL,
    AUTOMATION_SOURCE_APP,
)
from apps.rule_engine.models import Rule


class Command(BaseCommand):
    help = '校验 automation 规则与统一规则引擎镜像的一致性'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true', default=False,
            help='发现不一致时调用 bridge 重新同步',
        )

    def handle(self, *args, **options):
        fix = options['fix']
        from apps.automation.models import AutomationRule

        issues = []
        synced = 0

        active_rules = AutomationRule.objects.filter(deleted_at__isnull=True)
        for legacy in active_rules:
            unified = Rule.objects.filter(
                source_app=AUTOMATION_SOURCE_APP, legacy_id=legacy.id,
            ).first()
            if unified is None:
                issues.append(('MISSING', legacy.id, '未镜像到统一规则引擎'))
                if fix:
                    from apps.rule_engine.bridge import sync_automation_rule_to_unified
                    sync_automation_rule_to_unified(legacy)
                    synced += 1
                continue

            # 字段漂移比对（只比关键字段，避免噪音）
            drift = self._diff(legacy, unified)
            if drift:
                issues.append(('DRIFT', legacy.id, '; '.join(drift)))
                if fix:
                    from apps.rule_engine.bridge import sync_automation_rule_to_unified
                    sync_automation_rule_to_unified(legacy)
                    synced += 1

        # 应软删未软删：legacy 已软删，但统一侧仍 active
        deleted_rules = AutomationRule.objects.filter(deleted_at__isnull=False)
        for legacy in deleted_rules:
            unified = Rule.objects.filter(
                source_app=AUTOMATION_SOURCE_APP, legacy_id=legacy.id,
            ).first()
            if unified and unified.deleted_at is None:
                issues.append(('NOT_SOFT_DELETED', legacy.id,
                               'legacy 已软删但统一侧仍 active'))
                if fix:
                    from apps.rule_engine.bridge import sync_automation_rule_to_unified
                    sync_automation_rule_to_unified(legacy)
                    synced += 1

        # 输出
        total = active_rules.count() + deleted_rules.count()
        if issues:
            self.stdout.write(self.style.WARNING(
                f'[RULE_ENGINE] 发现 {len(issues)} 处不一致（共检查 {total} 条 automation 规则）'
            ))
            for kind, lid, detail in issues:
                self.stdout.write(f'  - {kind:16s} legacy_id={lid}  {detail}')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'[RULE_ENGINE] 一致：{total} 条 automation 规则镜像正常'
            ))

        if fix:
            self.stdout.write(self.style.SUCCESS(
                f'[RULE_ENGINE] --fix 已重新同步 {synced} 条'
            ))

        if issues and not fix:
            self.stdout.write(self.style.WARNING(
                '可加 --fix 重新同步以消除上述不一致。'
            ))
            raise SystemExit(1)

    @staticmethod
    def _diff(legacy, unified) -> list:
        """返回字段漂移说明列表（空表示一致）。"""
        drift = []
        if unified.name != legacy.name:
            drift.append(f'name: {unified.name!r} != {legacy.name!r}')
        if unified.enabled != bool(legacy.enabled):
            drift.append(f'enabled: {unified.enabled} != {bool(legacy.enabled)}')
        if unified.trigger_type != legacy.trigger_type:
            drift.append(f'trigger_type: {unified.trigger_type} != {legacy.trigger_type}')
        if unified.priority != legacy.priority:
            drift.append(f'priority: {unified.priority} != {legacy.priority}')
        # action_type 比对（统一侧首条 action）
        ua = unified.actions.first()
        if ua and ua.action_type != legacy.action_type:
            drift.append(f'action_type: {ua.action_type} != {legacy.action_type}')
        # condition 数量比对
        if unified.conditions.count() != len(legacy.condition_json or []):
            drift.append(
                f'condition_count: {unified.conditions.count()} '
                f'!= {len(legacy.condition_json or [])}'
            )
        return drift
