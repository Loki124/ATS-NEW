"""LIFE-3：将裸路径条件(CANDIDATE/DEMAND/POSITION)迁移到 METRIC 源（引用 MetricTemplate）。

背景（为什么这么设计）
----------------------
进入条件有两种条件源：
  1. 裸路径（legacy）：ConditionItem 当 condition_type ∈ {CANDIDATE, DEMAND, POSITION} 时，
     field 列存点路径字符串（如 candidate.age / demand.hiring_manager）。
  2. 指标模板（METRIC）：condition_type='METRIC'，field 存 MetricTemplate 的 id。

阶段规则的 skip_rules / archive_rules（JSONField）里同样有
condition_type ∈ {CANDIDATE, DEMAND, POSITION} 且 field=点路径 的项。

METRIC 求值器（apps/metrics/services/metric_engine.py:evaluate_metric_condition）最终也是按
模板指向的 AtomicMetric 的 source_path 取值 + 按 data_type 转换 —— 与裸路径求值**同源**。
因此把裸路径条件改写为 METRIC（引用一个指向同 source_path 的 AtomicMetric 的模板），
**求值结果不变**，只是把条件纳入指标模板治理体系（EXP-5 失效检测 + LIFE-2 禁用/删除披露）。

可靠性约束（硬纪律，必须遵守）
-----------------------------
  - 绝不硬造 data_type：只有按 source_path 查到 status='enabled' 的 AtomicMetric 时才迁移；
    查不到则 SKIP 并在报告中列出该路径。不猜测/创建带错误 data_type 的 AtomicMetric
    （那会伪造、导致求值错误 = 假绿）。
  - 零 schema 变更：不新增/修改任何 model 字段、不新增 migration 文件。
    ConditionItem.condition_type 的 choices 已含 'METRIC'（P0 已加），直接存 'METRIC' 合法。
  - 零新增依赖。
  - 真实可靠：dry-run 默认不写库；--apply 才写。

求值权威路径（已核实，无需再查）
-------------------------------
apps/entry_condition/services.py:270 与 :280 的求值循环直接
rule.items.filter(deleted_at__isnull=True)（ORM ConditionItem），**不读**
ProcessStageLink.entry_rule_expression 缓存。所以改 ConditionItem 即生效于准入。
entry_rule_expression 仅是展示缓存，本命令 best-effort 重建它（失败仅 warn 不致命）。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from apps.entry_condition.models import (
    ConditionFieldType,
    ConditionItem,
    EntryConditionRule,
)
from apps.metrics.models import (
    AtomicMetric,
    MetricStatus,
    MetricTemplate,
)
from apps.process.models import StageRule
from apps.rule_engine.models import UnifiedOperator


# 裸路径条件类型（STAGE_STATUS 不迁移 —— 它的语义是阶段名称 + 状态，非字段路径）
SOURCE_TYPES: List[str] = ['CANDIDATE', 'DEMAND', 'POSITION']

# 模板 id 可能字符集：36 位 UUID 仅含十六进制 + '-'；21 位 nanoid 默认字母表含大小写字母/数字/_-
_UUID_CHARS = set('0123456789abcdefABCDEF-')
_ID_ALPHABET = set('0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-_')


def _looks_like_id(field: Any) -> bool:
    """判断 field 是否已存模板 id（迁移后形态），避免重复迁移 / 误改已迁移项。

    裸路径必含 '.'（candidate.age / demand.hiring_manager / position.x），模板 id 是
    21 位 nanoid 或 36 位 UUID，均不含 '.'。故 no-dot 是主判据；再辅以长度 + 合法字符做
    二次确认，以覆盖 nanoid 默认字母表中可能含 '_' 的情况。
    """
    if not isinstance(field, str) or not field:
        return False
    if '.' in field:
        return False  # 裸路径（candidate.age）必含点
    if 21 <= len(field) <= 36 and all(c in _UUID_CHARS for c in field):
        return True
    if len(field) == 21 and all(c in _ID_ALPHABET for c in field):
        return True
    return False


class Command(BaseCommand):
    help = '将裸路径条件(CANDIDATE/DEMAND/POSITION)迁移到 METRIC 源(引用 MetricTemplate)。dry-run 默认。'

    def add_arguments(self, parser):
        parser.add_argument(
            '--apply', action='store_true',
            help='实际写入数据库；默认 dry-run（只报告、不写库）',
        )
        parser.add_argument(
            '--source-types', nargs='*', default=SOURCE_TYPES,
            help='要迁移的裸路径条件类型，默认 CANDIDATE DEMAND POSITION',
        )

    # ------------------------------------------------------------------
    # 模板解析：find-or-create 指向 am 的启用模板
    # ------------------------------------------------------------------
    def _resolve_template(self, am: AtomicMetric) -> MetricTemplate:
        """返回指向 am 的启用模板（复用既有，不存在则新建）。

        - 按 atomic_metric + status='enabled' 优先复用，避免重复创建。
        - 新建时 operators 取 UnifiedOperator 全集，保证原裸路径 condition 的 operator 在白名单内。
        - 若 name 已被别的模板占用触发 unique 冲突，抛 IntegrityError（由调用方捕获降级、不崩）。
        """
        template = MetricTemplate.objects.filter(
            atomic_metric=am, status=MetricStatus.ENABLED,
        ).first()
        if template is not None:
            return template
        return MetricTemplate.objects.create(
            name=am.name,  # AtomicMetric.name 唯一，模板也按此唯一
            atomic_metric=am,
            derived_metric=None,
            operators=list(UnifiedOperator.values),  # 全集，保证原 operator 在白名单内
            param_config={'min': None, 'max': None, 'step': None,
                          'prefix': '', 'suffix': '', 'allOption': False},
            value_domain={'segments': []},
            param_enums=[],
            param_allow_null=False,
            status=MetricStatus.ENABLED,
            description='auto-migrated from raw-path condition (LIFE-3)',
        )

    # ------------------------------------------------------------------
    # best-effort 重建 entry_rule_expression 展示缓存（不致命）
    # ------------------------------------------------------------------
    def _rebuild_entry_rule_expression(self, rule: EntryConditionRule) -> None:
        """重建 link.entry_rule_expression 展示缓存（结构对齐 FE 写入形态）。

        - 仅基于迁移后的 ORM ConditionItem 重建；失败仅打印 warning，绝不导致整条迁移失败。
        - entry_rule_expression 是 CharField(max_length=500)，重建后超长则跳过缓存更新并 warn。
        """
        link = rule.link
        if link is None:
            return
        items = rule.items.filter(deleted_at__isnull=True).order_by('item_seq')
        condition_type = items[0].condition_type if items else ConditionFieldType.METRIC
        payload = {
            'matchType': rule.match_type or 'ALL',
            'conditionType': condition_type,
            'items': [
                {
                    'seq': ci.item_seq,
                    'type': ci.condition_type,
                    'field': ci.field,
                    'operator': ci.operator,
                    'value': ci.value,
                }
                for ci in items
            ],
        }
        encoded = json.dumps(payload, ensure_ascii=False)
        if len(encoded) > 500:
            self.stderr.write(self.style.WARNING(
                f'  [WARN] link {link.id} entry_rule_expression 重建后长度 {len(encoded)} > 500，'
                f'跳过缓存更新（展示缓存不一致，不影响准入求值）'))
            return
        link.entry_rule_expression = encoded
        link.save(update_fields=['entry_rule_expression', 'updated_at'])

    # ------------------------------------------------------------------
    # JSON 规则列表（skip_rules / archive_rules）改写
    # ------------------------------------------------------------------
    def _rewrite_json_items(
        self,
        rules_list: Any,
        source_types: List[str],
        dry_run: bool,
        prefix: str,
        sr_id: str,
        bucket: str,
    ) -> Tuple[List[Any], int, int, int]:
        """改写单个 JSON 规则列表里的裸路径 item。

        返回 (new_rules_list, scanned, migrated, err_count)。
        - 不在此处写库；dry-run 时返回的 new_list 与原列表内容一致（不改写 item 本身）。
        - 查不到 AtomicMetric 的项计入 self._skipped_no_atomic（调用方实例属性）。
        - 单条异常计入 err_count 并打印，不中断整批。
        """
        scanned = 0
        migrated = 0
        err_count = 0
        if not isinstance(rules_list, list):
            return rules_list, scanned, migrated, err_count

        new_rules: List[Any] = []
        for rule_dict in rules_list:
            if not isinstance(rule_dict, dict):
                new_rules.append(rule_dict)
                continue
            items = rule_dict.get('items')
            if not isinstance(items, list):
                new_rules.append(rule_dict)
                continue

            new_items: List[Any] = []
            for item in items:
                scanned += 1
                if not isinstance(item, dict):
                    new_items.append(item)
                    continue
                ctype = item.get('condition_type')
                field = item.get('field')
                # 仅处理裸路径（在 source_types 内且 field 非模板 id）的项
                if ctype in source_types and not _looks_like_id(field):
                    path = field
                    try:
                        am = AtomicMetric.objects.filter(
                            source_path=path, status=MetricStatus.ENABLED,
                        ).first()
                    except Exception as exc:  # noqa: BLE001 — 单条查询异常不中断整批
                        err_count += 1
                        self.stderr.write(self.style.ERROR(
                            f'  [ERROR] StageRule {sr_id} {bucket} 查 AtomicMetric 异常 '
                            f'path={path!r}: {exc}'))
                        new_items.append(item)
                        continue
                    if am is None:
                        self._skipped_no_atomic[path] = self._skipped_no_atomic.get(path, 0) + 1
                        new_items.append(item)
                        continue
                    migrated += 1
                    if dry_run:
                        # dry-run 不写库：仅描述将要改写，绝不创建/复用模板
                        self.stdout.write(
                            f'{prefix}将改写 StageRule {sr_id} {bucket} item: '
                            f'{ctype} {path} -> METRIC (待建/复用模板)')
                        new_items.append(item)  # dry-run 不改写原 item
                    else:
                        try:
                            template = self._resolve_template(am)
                        except IntegrityError as exc:
                            # 模板 name 被别的模板占用等唯一约束冲突：降级跳过该条，不崩
                            err_count += 1
                            self.stderr.write(self.style.ERROR(
                                f'  [ERROR] StageRule {sr_id} {bucket} 建模板冲突 path={path!r}: {exc}'))
                            migrated -= 1
                            new_items.append(item)
                            continue
                        new_item = dict(item)
                        new_item['condition_type'] = ConditionFieldType.METRIC
                        new_item['field'] = str(template.id)
                        new_items.append(new_item)
                else:
                    new_items.append(item)
            new_rule = dict(rule_dict)
            new_rule['items'] = new_items
            new_rules.append(new_rule)
        return new_rules, scanned, migrated, err_count

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        dry_run = not options['apply']
        source_types = list(options['source_types'] or SOURCE_TYPES)
        prefix = '[DRY-RUN] ' if dry_run else ''

        self._skipped_no_atomic: Dict[str, int] = {}
        migrated_entry = 0
        migrated_stage = 0
        errors = 0

        # 去重收集需要重建缓存的 EntryConditionRule（ORM 路径迁移后）
        rules_to_rebuild = set()

        # ---- 1) 进入条件（ORM ConditionItem） ----
        entry_scanned = 0
        cis = (
            ConditionItem.objects
            .filter(condition_type__in=source_types, deleted_at__isnull=True)
            .select_related('rule', 'rule__link')
            .order_by('id')
        )
        for ci in cis:
            entry_scanned += 1
            try:
                # 已迁移（METRIC）或 field 已是模板 id（无点）→ 跳过，不计入待迁移
                if ci.condition_type == ConditionFieldType.METRIC or _looks_like_id(ci.field):
                    continue
                path = ci.field
                am = AtomicMetric.objects.filter(
                    source_path=path, status=MetricStatus.ENABLED,
                ).first()
                if am is None:
                    self._skipped_no_atomic[path] = self._skipped_no_atomic.get(path, 0) + 1
                    continue
                if dry_run:
                    # dry-run 不写库：仅描述将要改写，绝不创建/复用模板
                    self.stdout.write(
                        f'{prefix}将改写 ConditionItem {ci.id}: '
                        f'{ci.condition_type} {path} -> METRIC (待建/复用模板)')
                else:
                    template = self._resolve_template(am)
                    ci.condition_type = ConditionFieldType.METRIC
                    ci.field = str(template.id)
                    ci.save(update_fields=['condition_type', 'field', 'updated_at'])
                    if ci.rule_id:
                        rules_to_rebuild.add(ci.rule_id)
                migrated_entry += 1
            except IntegrityError as exc:
                errors += 1
                self.stderr.write(self.style.ERROR(
                    f'  [ERROR] ConditionItem {ci.id} 建模板冲突 path={ci.field!r}: {exc}'))
            except Exception as exc:  # noqa: BLE001 — 单条出错不中断整批
                errors += 1
                self.stderr.write(self.style.ERROR(
                    f'  [ERROR] ConditionItem {ci.id} 处理异常: {exc}'))

        # ---- 2) skip / archive（JSON StageRule） ----
        stage_scanned = 0
        srs = StageRule.objects.select_related('link').all()
        for sr in srs:
            try:
                skip_rules = sr.skip_rules
                archive_rules = sr.archive_rules
                if not isinstance(skip_rules, list):
                    skip_rules = []
                if not isinstance(archive_rules, list):
                    archive_rules = []

                new_skip, s_scanned, s_mig, s_err = self._rewrite_json_items(
                    skip_rules, source_types, dry_run, prefix, str(sr.id), 'skip_rules')
                new_archive, a_scanned, a_mig, a_err = self._rewrite_json_items(
                    archive_rules, source_types, dry_run, prefix, str(sr.id), 'archive_rules')
                stage_scanned += s_scanned + a_scanned
                migrated_stage += s_mig + a_mig
                errors += s_err + a_err

                if not dry_run and (s_mig or a_mig):
                    update_fields = []
                    if new_skip != skip_rules:
                        sr.skip_rules = new_skip
                        update_fields.append('skip_rules')
                    if new_archive != archive_rules:
                        sr.archive_rules = new_archive
                        update_fields.append('archive_rules')
                    if update_fields:
                        update_fields.append('updated_at')
                        sr.save(update_fields=update_fields)
            except Exception as exc:  # noqa: BLE001 — 单条 StageRule 出错不中断整批
                errors += 1
                self.stderr.write(self.style.ERROR(
                    f'  [ERROR] StageRule {sr.id} 处理异常: {exc}'))

        # ---- 3) best-effort 重建 entry_rule_expression（仅 --apply） ----
        if not dry_run and rules_to_rebuild:
            for rule_id in sorted(rules_to_rebuild):
                try:
                    rule = EntryConditionRule.objects.select_related('link').get(pk=rule_id)
                    self._rebuild_entry_rule_expression(rule)
                except Exception as exc:  # noqa: BLE001 — 缓存重建失败仅 warn，不致命
                    self.stderr.write(self.style.WARNING(
                        f'  [WARN] 重建 entry_rule_expression 失败 rule={rule_id}: {exc}'))

        # ---- 4) 报告 ----
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('=== LIFE-3 裸路径条件 → METRIC 迁移报告 ==='))
        self.stdout.write(
            f'{prefix}扫描：进入条件项 {entry_scanned} 条，阶段规则项 {stage_scanned} 条')
        self.stdout.write(
            f'{prefix}已迁移：进入条件 {migrated_entry} 条，'
            f'skip/archive 项 {migrated_stage} 条')
        if self._skipped_no_atomic:
            parts = ', '.join(
                f'{k}: {v}' for k, v in sorted(self._skipped_no_atomic.items()))
            self.stdout.write(
                f'{prefix}SKIP(无对应 enabled AtomicMetric)：{parts}')
        if errors:
            self.stdout.write(self.style.WARNING(f'{prefix}处理异常条数：{errors}'))

        total_migrated = migrated_entry + migrated_stage
        if dry_run:
            self.stdout.write(self.style.WARNING(
                'DRY-RUN 完成：未做任何写入。使用 --apply 实际迁移。'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'迁移完成：共改写 {total_migrated} 条条件项'
                f'（进入 {migrated_entry} / 阶段 {migrated_stage}）。'))
