"""检查 automation / entry_condition / time_limit / campus_control / mou 规则与统一规则引擎镜像的一致性（Phase 4）。

用途：
- 灰度期验证双写（RULE_ENGINE_DOUBLE_WRITE）是否把所有 legacy 规则正确镜像；
- 发现「缺失镜像 / 字段漂移 / 应软删未软删」三类不一致。

Phase 3（2026-08-31）扩展：新增 entry_condition / time_limit 两个 source_app。
Phase 4（2026-09-01）扩展：新增 campus_control（CONSTRAINT / OFFER_SUBMITTED）与
mou（TCA / BUSINESS_EVENT / SET_PERMISSION）两个 source_app 的同类比对与 --fix 重同步
（见设计文档 §3.5 / §3.6 / §6）。campus/mou 用硬删 + is_active，无统一软删行，故
deleted_qs 为空；其硬删行的统一镜像由各自 signals.post_delete 软删。

用法：
    python manage.py check_rule_engine_consistency
    python manage.py check_rule_engine_consistency --fix     # 重新同步以消除不一致

退出码：发现不一致且非 --fix 时为 1，否则 0（便于 CI 断言）。
"""
from django.core.management.base import BaseCommand

from apps.rule_engine.bridge import (
    AUTOMATION_SOURCE_APP,
    CAMPUS_CONTROL_SOURCE_APP,
    ENTRY_CONDITION_SOURCE_APP,
    MOU_SOURCE_APP,
    TIME_LIMIT_SOURCE_APP,
    sync_automation_rule_to_unified,
    sync_control_rule_to_unified,
    sync_entry_condition_rule_to_unified,
    sync_mou_rule_to_unified,
    sync_time_limit_rule_to_unified,
)
from apps.rule_engine.models import Rule


class Command(BaseCommand):
    help = '校验 automation / entry_condition / time_limit / campus_control / mou 规则与统一规则引擎镜像的一致性'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix', action='store_true', default=False,
            help='发现不一致时调用 bridge 重新同步',
        )

    def handle(self, *args, **options):
        self.fix = options['fix']
        self.issues = []
        self.synced = 0
        self.total = 0

        # ---- automation（Phase 2）----
        from apps.automation.models import AutomationRule
        self._check_source_app(
            AUTOMATION_SOURCE_APP,
            active_qs=AutomationRule.objects.filter(deleted_at__isnull=True),
            deleted_qs=AutomationRule.objects.filter(deleted_at__isnull=False),
            diff_fn=self._diff_automation,
            sync_fn=sync_automation_rule_to_unified,
        )

        # ---- entry_condition（Phase 3）----
        from apps.entry_condition.models import EntryConditionRule
        self._check_source_app(
            ENTRY_CONDITION_SOURCE_APP,
            active_qs=EntryConditionRule.objects.filter(deleted_at__isnull=True),
            deleted_qs=EntryConditionRule.objects.filter(deleted_at__isnull=False),
            diff_fn=self._diff_entry_condition,
            sync_fn=sync_entry_condition_rule_to_unified,
        )

        # ---- time_limit（Phase 3）----
        from apps.time_limit.models import TimeLimitRule
        self._check_source_app(
            TIME_LIMIT_SOURCE_APP,
            active_qs=TimeLimitRule.objects.filter(deleted_at__isnull=True),
            deleted_qs=TimeLimitRule.objects.filter(deleted_at__isnull=False),
            diff_fn=self._diff_time_limit,
            sync_fn=sync_time_limit_rule_to_unified,
        )

        # ---- campus_control（Phase 4）----
        # campus ControlRule 用硬删 + is_active（无统一软删语义），故 active_qs 取全部
        # 现存行；deleted_qs 为空（不存在软删行）。硬删行的统一镜像由 signals.post_delete
        # 软删，孤儿由本命令的 active_qs 比对自然覆盖（无对应 legacy 行即不再新增）。
        from apps.campus_control.models import ControlRule
        self._check_source_app(
            CAMPUS_CONTROL_SOURCE_APP,
            active_qs=ControlRule.objects.all(),
            deleted_qs=ControlRule.objects.none(),
            diff_fn=self._diff_campus_control,
            sync_fn=sync_control_rule_to_unified,
        )

        # ---- mou（Phase 4）----
        # MouRule 无独立软删（硬删 + is_active），同 campus 处理：active_qs 取全部现存行。
        from apps.mou.models import MouRule
        self._check_source_app(
            MOU_SOURCE_APP,
            active_qs=MouRule.objects.all(),
            deleted_qs=MouRule.objects.none(),
            diff_fn=self._diff_mou,
            sync_fn=sync_mou_rule_to_unified,
        )

        # 输出
        if self.issues:
            self.stdout.write(self.style.WARNING(
                f'[RULE_ENGINE] 发现 {len(self.issues)} 处不一致（共检查 {self.total} 条规则）'
            ))
            for kind, app, lid, detail in self.issues:
                self.stdout.write(f'  - {kind:16s} [{app}] legacy_id={lid}  {detail}')
        else:
            self.stdout.write(self.style.SUCCESS(
                f'[RULE_ENGINE] 一致：{self.total} 条规则镜像正常'
            ))

        if self.fix and self.synced:
            self.stdout.write(self.style.SUCCESS(
                f'[RULE_ENGINE] --fix 已重新同步 {self.synced} 条'
            ))

        if self.issues and not self.fix:
            self.stdout.write(self.style.WARNING(
                '可加 --fix 重新同步以消除上述不一致。'
            ))
            raise SystemExit(1)

    # ------------------------------------------------------------------
    # 通用比对核心
    # ------------------------------------------------------------------
    def _check_source_app(self, source_app, active_qs, deleted_qs, diff_fn, sync_fn):
        self.total += active_qs.count() + deleted_qs.count()

        # 缺失镜像 / 字段漂移
        for legacy in active_qs:
            unified = Rule.objects.filter(
                source_app=source_app, legacy_id=legacy.id,
            ).first()
            if unified is None:
                self.issues.append(
                    ('MISSING', source_app, legacy.id, '未镜像到统一规则引擎'))
                if self.fix:
                    sync_fn(legacy)
                    self.synced += 1
                continue

            drift = diff_fn(legacy, unified)
            if drift:
                self.issues.append(
                    ('DRIFT', source_app, legacy.id, '; '.join(drift)))
                if self.fix:
                    sync_fn(legacy)
                    self.synced += 1

        # 应软删未软删：legacy 已软删，但统一侧仍 active
        for legacy in deleted_qs:
            unified = Rule.objects.filter(
                source_app=source_app, legacy_id=legacy.id,
            ).first()
            if unified and unified.deleted_at is None:
                self.issues.append(
                    ('NOT_SOFT_DELETED', source_app, legacy.id,
                     'legacy 已软删但统一侧仍 active'))
                if self.fix:
                    sync_fn(legacy)
                    self.synced += 1

    # ------------------------------------------------------------------
    # 各 app 字段漂移比对（只比关键字段，避免噪音）
    # ------------------------------------------------------------------
    @staticmethod
    def _diff_automation(legacy, unified) -> list:
        drift = []
        if unified.name != legacy.name:
            drift.append(f'name: {unified.name!r} != {legacy.name!r}')
        if unified.enabled != bool(legacy.enabled):
            drift.append(f'enabled: {unified.enabled} != {bool(legacy.enabled)}')
        if unified.trigger_type != legacy.trigger_type:
            drift.append(f'trigger_type: {unified.trigger_type} != {legacy.trigger_type}')
        if unified.priority != legacy.priority:
            drift.append(f'priority: {unified.priority} != {legacy.priority}')
        ua = unified.actions.first()
        if ua and ua.action_type != legacy.action_type:
            drift.append(f'action_type: {ua.action_type} != {legacy.action_type}')
        if unified.conditions.count() != len(legacy.condition_json or []):
            drift.append(
                f'condition_count: {unified.conditions.count()} '
                f'!= {len(legacy.condition_json or [])}'
            )
        return drift

    @staticmethod
    def _diff_entry_condition(legacy, unified) -> list:
        drift = []
        if unified.name != legacy.rule_name:
            drift.append(f'name: {unified.name!r} != {legacy.rule_name!r}')
        legacy_enabled = (legacy.status == 'ENABLED')
        if unified.enabled != legacy_enabled:
            drift.append(f'enabled: {unified.enabled} != {legacy_enabled}')
        if unified.trigger_type != 'STAGE_ENTERED':
            drift.append(f'trigger_type: {unified.trigger_type} != STAGE_ENTERED')
        if unified.priority_rank != legacy.rule_seq:
            drift.append(f'priority_rank: {unified.priority_rank} != {legacy.rule_seq}')
        # 条件数量比对（仅未软删项）
        active_items = legacy.items.filter(deleted_at__isnull=True).count()
        if unified.conditions.count() != active_items:
            drift.append(
                f'condition_count: {unified.conditions.count()} != {active_items}')
        # 动作类型比对（统一侧固定 ALLOW）
        ua = unified.actions.first()
        if ua and ua.action_type != 'ALLOW':
            drift.append(f'action_type: {ua.action_type} != ALLOW')
        return drift

    @staticmethod
    def _diff_time_limit(legacy, unified) -> list:
        drift = []
        if unified.name != legacy.rule_name:
            drift.append(f'name: {unified.name!r} != {legacy.rule_name!r}')
        if unified.enabled != bool(legacy.enabled):
            drift.append(f'enabled: {unified.enabled} != {bool(legacy.enabled)}')
        if unified.trigger_type != 'STAGE_DWELL_TIMEOUT':
            drift.append(f'trigger_type: {unified.trigger_type} != STAGE_DWELL_TIMEOUT')
        if unified.priority_rank != legacy.priority:
            drift.append(f'priority_rank: {unified.priority_rank} != {legacy.priority}')
        ua = unified.actions.first()
        if ua:
            if ua.action_type != 'LOCK':
                drift.append(f'action_type: {ua.action_type} != LOCK')
            else:
                p = ua.params_json or {}
                if p.get('lock_duration') != legacy.lock_duration:
                    drift.append(
                        f'lock_duration: {p.get("lock_duration")} != {legacy.lock_duration}')
                if p.get('extension_per_person') != legacy.extension_per_person:
                    drift.append(
                        f'extension_per_person: {p.get("extension_per_person")} '
                        f'!= {legacy.extension_per_person}')
                if p.get('effective_scope') != legacy.effective_scope:
                    drift.append(
                        f'effective_scope: {p.get("effective_scope")} '
                        f'!= {legacy.effective_scope}')
        if unified.conditions.count() != len(legacy.conditions or []):
            drift.append(
                f'condition_count: {unified.conditions.count()} '
                f'!= {len(legacy.conditions or [])}')
        return drift

    @staticmethod
    def _diff_campus_control(legacy, unified) -> list:
        drift = []
        if unified.name != (legacy.code or str(legacy.id)):
            drift.append(f'name: {unified.name!r} != {legacy.code!r}')
        legacy_enabled = bool(getattr(legacy, 'is_active', True))
        if unified.enabled != legacy_enabled:
            drift.append(f'enabled: {unified.enabled} != {legacy_enabled}')
        if unified.trigger_type != 'OFFER_SUBMITTED':
            drift.append(f'trigger_type: {unified.trigger_type} != OFFER_SUBMITTED')
        ua = unified.actions.first()
        expected_action = (
            'BLOCK_HARD' if getattr(legacy, 'strength', '') == '硬约束' else 'BLOCK_SOFT'
        )
        if ua and ua.action_type != expected_action:
            drift.append(f'action_type: {ua.action_type} != {expected_action}')
        # config 关键字段
        cfg = unified.config_json or {}
        legacy_target = float(getattr(legacy, 'target', 0) or 0)
        if cfg.get('target') != legacy_target:
            drift.append(f'target: {cfg.get("target")} != {legacy_target}')
        if cfg.get('strength') != getattr(legacy, 'strength', None):
            drift.append(f'strength: {cfg.get("strength")} != {getattr(legacy, "strength", None)}')
        return drift

    @staticmethod
    def _diff_mou(legacy, unified) -> list:
        drift = []
        if unified.name != getattr(legacy, 'name', ''):
            drift.append(f'name: {unified.name!r} != {getattr(legacy, "name", "")!r}')
        legacy_enabled = bool(getattr(legacy, 'is_active', True))
        if unified.enabled != legacy_enabled:
            drift.append(f'enabled: {unified.enabled} != {legacy_enabled}')
        if unified.trigger_type != 'BUSINESS_EVENT':
            drift.append(f'trigger_type: {unified.trigger_type} != BUSINESS_EVENT')
        ua = unified.actions.first()
        if ua and ua.action_type != 'SET_PERMISSION':
            drift.append(f'action_type: {ua.action_type} != SET_PERMISSION')
        cfg = unified.config_json or {}
        if cfg.get('event') != getattr(legacy, 'trigger_event', None):
            drift.append(
                f'event: {cfg.get("event")!r} != {getattr(legacy, "trigger_event", None)!r}')
        return drift
        return drift
