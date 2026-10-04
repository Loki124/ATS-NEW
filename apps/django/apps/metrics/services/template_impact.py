"""LIFE-2：指标模板禁用/删除前的受影响规则枚举（事前披露 + 确认闸门）。

背景（P2 生命周期治理）：
    指标模板（MetricTemplate）被规则引用有两种落点：
      1. 进入条件（ORM）：entry_condition.ConditionItem，condition_type='METRIC'
         时 field 列存模板 id（字符串），通过 FK rule 归属 EntryConditionRule，
         后者 FK link 到 process.ProcessStageLink。
      2. 跳过/归档规则（JSON）：process.StageRule 的 skip_rules / archive_rules
         两个 JSONField，每条 rule 的 items[] 中 condition_type='METRIC' 的项，
         field 存模板 id。

目标：管理员在禁用/删除模板前，系统先枚举所有引用该模板的规则，供前端弹窗展示
清单 + 处理建议，确认后再执行。

硬约束（务必遵守）：
    - 零 schema 变更：不新增/修改任何 model 字段、不新增 migration。纯查询。
    - 真实可靠：枚举必须真实命中存量数据，不可伪造。
    - 对异常不吞掉：本函数为纯查询，异常（含 MetricTemplate.DoesNotExist）
      交由视图层处理，便于返回 404。
"""
from typing import Any, Dict, List

from apps.entry_condition.models import ConditionItem, EntryConditionRule
from apps.metrics.models import MetricTemplate
from apps.process.models import StageRule


def _link_owner(link: Any) -> Dict[str, str]:
    """从流程-阶段关联（ProcessStageLink）解析归属信息。

    Args:
        link: ProcessStageLink 实例，含 process / stage / custom_name。

    Returns:
        dict: 含 process_id / process_name / stage_id / stage_name 四键。
        stage_name 优先取 link.custom_name（流程内显示名），否则回退 stage.name。
    """
    process = link.process
    stage = link.stage
    return {
        'process_id': str(process.id),
        'process_name': process.name,
        'stage_id': str(stage.id) if stage is not None else '',
        'stage_name': link.custom_name or (stage.name if stage is not None else ''),
    }


def get_template_affected_rules(template_id: str) -> Dict[str, Any]:
    """返回引用某指标模板的全部规则（进入条件 ORM + skip/archive JSON）。

    零 schema 变更，纯查询。

    Args:
        template_id: 指标模板 id（字符串，与存储的 field 值同型）。

    Returns:
        dict: 结构见下方组装逻辑，含 template_id / template_name /
        template_status / total / entry_conditions / stage_rules。

    Raises:
        MetricTemplate.DoesNotExist: 模板不存在时由 .get() 抛出，交由视图层返回 404。
    """
    tid = str(template_id)

    # 取模板元信息：不存在则抛出 MetricTemplate.DoesNotExist（视图层捕获 → 404）。
    template = MetricTemplate.objects.get(id=tid)

    entry_conditions: List[Dict[str, Any]] = []
    stage_rules: List[Dict[str, Any]] = []

    # ===== 1. 进入条件（ORM 路径） =====
    # ConditionItem 与 EntryConditionRule 均为软删模型：deleted_at__isnull=True
    # 过滤已删除项与已删除规则，避免披露已失效的引用（真实可靠，不假绿）。
    items = (
        ConditionItem.objects
        .filter(
            condition_type='METRIC',
            field=tid,
            deleted_at__isnull=True,
            rule__deleted_at__isnull=True,
        )
        .select_related('rule__link__process', 'rule__link__stage')
        .order_by('rule__link__process__name', 'rule__rule_name', 'item_seq')
    )
    for ci in items:
        rule = ci.rule
        link = rule.link
        owner = _link_owner(link)
        entry_conditions.append({
            'rule_id': str(rule.id),
            'rule_name': rule.rule_name,
            'rule_status': rule.status,
            'expression': rule.expression,
            'item_id': str(ci.id),
            'operator': ci.operator,
            'value': ci.value,
            **owner,
        })

    # ===== 2. 跳过/归档规则（JSON 路径） =====
    # StageRule 无软删（硬删模型），但 skip_rules / archive_rules 是 JSONField，
    # 遍历每条规则列表，扫描 items[] 中 condition_type='METRIC' 且 field 命中模板的项。
    stage_rule_qs = (
        StageRule.objects
        .select_related('link__process', 'link__stage')
        .all()
    )
    for sr in stage_rule_qs:
        link = sr.link
        owner = _link_owner(link)
        for rule_type, rules in (
            ('skip', sr.skip_rules or []),
            ('archive', sr.archive_rules or []),
        ):
            if not isinstance(rules, list):
                continue
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                items_list = rule.get('items') or []
                if not isinstance(items_list, list):
                    continue
                for idx, item in enumerate(items_list):
                    if not isinstance(item, dict):
                        continue
                    if (
                        item.get('condition_type') == 'METRIC'
                        and str(item.get('field')) == tid
                    ):
                        stage_rules.append({
                            'rule_type': rule_type,
                            'stage_rule_id': str(sr.id),
                            'rule_id': str(rule.get('id')),
                            'rule_name': rule.get('name') or '',
                            'rule_enabled': bool(rule.get('enabled')),
                            'item_id': idx,
                            'operator': item.get('operator') or '',
                            'value': item.get('value'),
                            **owner,
                        })

    total = len(entry_conditions) + len(stage_rules)
    return {
        'template_id': tid,
        'template_name': template.name,
        'template_status': template.status,
        'version_count': template.version_count,
        'total': total,
        'entry_conditions': entry_conditions,
        'stage_rules': stage_rules,
    }
