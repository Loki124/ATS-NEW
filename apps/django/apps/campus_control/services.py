"""人员比例管控系统 — 规则服务层（T03：副本 / 启用校验 / Offer 钩子）。

设计约束（用户拍板 3 项修订）：
  ① Candidate 扩展 school_tag / major_tag，Offer 钩子实现「性别 + 院校标签 + 专业标签」全维度命中。
  ② 去掉 handling_method；仅 strength（控制强度）单字段驱动：硬约束→阻断；软约束/仅提示→放行+提示。
  ③ unique_together 含 is_active：启用原规则 + 未启用副本可共存；副本启用冲突由 validate_rule_unique 拦截。

口径铁律：计数 MUST REUSE calc.py 的 _COUNTED_STATUSES / rule_matches / _indicator_filter /
_accounting_month / count_rule，禁止另写一套计数逻辑，避免与 ratio 看板漂移。

为规避 campus_control.views ↔ campus_control.services 循环 import，
views 的 _person_to_dict / _build_person_dim_map / _rule_to_dict 在本模块内惰性 import。
"""
from datetime import date, datetime
from decimal import Decimal

from django.db import IntegrityError

from .calc import (
    _COUNTED_STATUSES, rule_matches, _indicator_filter, _accounting_month, count_rule,
)
from .constants import STRENGTH
from .models import ControlRule, Person


class ControlRuleViolation(Exception):
    """规则冲突 / 命中阻断异常。

    - status_code: 409（启用冲突）/ 400（占比超 100% / Offer 硬约束阻断）。
    - blocks / warnings: Offer 钩子命中明细（含规则 code、维度·指标、适用范围、年度/月度、当前数/目标数）。
    """

    def __init__(self, message='', status_code=400, blocks=None, warnings=None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.blocks = blocks or []
        self.warnings = warnings or []

    def __str__(self):
        return self.message


# ── 维度 → 候选人字段映射（_dim_field 已覆盖 legacy 三维度，这里显式用于维度命中判断）──
_DIM_CANDIDATE_FIELD = {
    '性别': 'gender',
    '院校标签': 'school_tag',
    '专业标签': 'major_tag',
}


def _scope_text(rule) -> str:
    """适用范围展示文本：全空显示「全局」。"""
    parts = [rule.bu or '全局', rule.position or '职务不限', rule.level or '职级不限']
    return '·'.join(parts)


def _views_helpers():
    """惰性导入 views 的辅助函数，规避循环 import。"""
    from .views import _person_to_dict, _build_person_dim_map, _rule_to_dict
    return _person_to_dict, _build_person_dim_map, _rule_to_dict


def copy_rule(rule):
    """克隆一条规则为「未启用副本」（is_active=False，重新补号）。

    返回新建的 ControlRule（code 由 save() 自动补号）。
    若源已 is_active=False 再复制 → 两条未启用同键 → save() 触发 unique 冲突 → 调用方捕获
    IntegrityError 返回 409「该组合已存在未启用副本」。
    """
    clone = ControlRule(
        bu=rule.bu, position=rule.position, level=rule.level,
        dimension=rule.dimension, indicator=rule.indicator, year=rule.year,
        target=rule.target, strength=rule.strength,
        annual_target=rule.annual_target,
        monthly_targets=list(rule.monthly_targets) if isinstance(rule.monthly_targets, (list, tuple)) else [0] * 12,
        is_active=False,
    )
    # save() 自动补唯一 code；若与现存未启用副本撞键 → IntegrityError
    clone.save()
    return clone


def validate_rule_unique(rule):
    """统一启用校验（副本启用前调用）：唯一含状态 + 占比≤100%。

    冲突 → 409「该组合已存在启用规则，请改键或停用原规则」
    占比超 → 400「该适用范围下此维度指标目标占比之和不得超过 100%」
    """
    # 1) 唯一含状态：启用键下不得存在另一条同键启用规则
    conflict = ControlRule.objects.filter(
        bu=rule.bu, position=rule.position, level=rule.level,
        dimension=rule.dimension, indicator=rule.indicator, year=rule.year,
        is_active=True,
    ).exclude(pk=rule.pk).exists()
    if conflict:
        raise ControlRuleViolation('该组合已存在启用规则，请改键或停用原规则', status_code=409)

    # 2) 占比加和 ≤ 100%（仅统计启用规则）
    existing = ControlRule.objects.filter(
        bu=rule.bu, position=rule.position, level=rule.level,
        dimension=rule.dimension, year=rule.year, is_active=True,
    ).exclude(pk=rule.pk)
    s = sum((r.target for r in existing), Decimal('0')) + (rule.target or Decimal('0'))
    if s > Decimal('1') + Decimal('0.0001'):
        pct = (s * 100).quantize(Decimal('0.01'))
        raise ControlRuleViolation(
            f'该适用范围下此维度指标目标占比之和不得超过 100%，当前为 {pct}%', status_code=400,
        )


def toggle_rule(rule, is_active: bool):
    """停用/启用规则。

    停用(False)：直接置 is_active=False 保存。
    启用(True)：先跑统一校验（validate_rule_unique），冲突/占比超分别 409/400；校验通过才启用。
    """
    if not is_active:
        rule.is_active = False
        rule.save(update_fields=['is_active'])
        return rule
    # 启用：先校验（副本启用可能撞启用原规则 / 占比超）
    validate_rule_unique(rule)
    rule.is_active = True
    rule.save(update_fields=['is_active'])
    return rule


def validate_offer_against_rules(*, candidate, position, level, position_title, start_date):
    """Offer 创建钩子：评估本条 offer 真命中的启用规则，按 strength 收集 BLOCK / WARN。

    计数严格复用 calc.py（_COUNTED_STATUSES / rule_matches / _indicator_filter /
    _accounting_month / count_rule），口径与 ratio 看板一致。

    参数：
      candidate: Candidate 实例（读 gender / school_tag / major_tag）
      position: Position 实例（读 department.name 作为 bu；风险 3：须与 DEPTS 取值对齐）
      level / position_title: offer 的职级 / 职务文本
      start_date: date 或 None（None 时跳过月度判定，仅年度计数）

    返回：{'blocks': [...], 'warnings': [...]}
      命中硬约束 → 抛 ControlRuleViolation(blocks=..., warnings=...)，由调用方转 400/409 回滚。
      仅软约束/仅提示命中 → 返回 dict（warnings 非空），调用方 logger.warning 放行。
    """
    _person_to_dict, _build_person_dim_map, _rule_to_dict = _views_helpers()

    # a. 构造人员数据集 = 现有 Person + 一条合成人员（代表本条 offer）
    dim_map = _build_person_dim_map()
    persons = [_person_to_dict(p, dim_map) for p in Person.objects.all()]

    # 合成人员：其 bu/school/sex/major 直接取 offer/candidate，使其自然计入命中规则
    dept_name = ''
    if position and getattr(position, 'department', None):
        dept_name = position.department.name
    synthetic = {
        'bu': dept_name,
        'school': getattr(candidate, 'school_tag', '') or '',
        'sex': getattr(candidate, 'gender', '') or '',
        'major': getattr(candidate, 'major_tag', '') or '',
        'month': f'{start_date.month}月' if isinstance(start_date, date) else None,
        'status': '在途待入职',
        'expected_entry_date': start_date.isoformat() if isinstance(start_date, date) else None,
        'actual_entry_date': None,
        'counted': True,
        'position': position_title or '',
        'level': level or '',
    }
    persons_with_synthetic = persons + [synthetic]

    # b. offer 维度命中所需的候选人取值
    cand_dim_value = {
        '性别': getattr(candidate, 'gender', '') or '',
        '院校标签': getattr(candidate, 'school_tag', '') or '',
        '专业标签': getattr(candidate, 'major_tag', '') or '',
    }
    offer_scope = {
        'bu': dept_name,
        'position': position_title or '',
        'level': level or '',
    }

    blocks = []
    warnings = []
    year = start_date.year if isinstance(start_date, date) else None
    month_label = f'{start_date.month}月' if isinstance(start_date, date) else None

    # c. 遍历启用规则；仅评估「本条 offer 真命中」的规则
    for rule in ControlRule.objects.filter(is_active=True):
        # 年度过滤（start_date 存在时；否则评估全部启用规则）
        if year is not None and rule.year != year:
            continue

        rule_dict = _rule_to_dict(rule)
        dim_name = rule_dict['dimension']
        ind_name = rule_dict['indicator']

        # 适用范围命中（规则字段非空才要求相等；空=全局）
        # rule_matches(p, rule)：person(offer_scope) 命中 rule 的适用范围。
        scope_hit = rule_matches(offer_scope, rule_dict)
        # 维度命中：候选人在该维度的取值 == 规则指标
        dim_hit = (dim_name in cand_dim_value) and (cand_dim_value[dim_name] == ind_name)
        if not (scope_hit and dim_hit):
            continue

        # 仅本条 offer 真命中该规则才继续计数
        annual_count = count_rule(rule_dict, persons_with_synthetic)

        month_target = 0
        month_count = 0
        if isinstance(start_date, date):
            mt = rule_dict.get('monthly_targets') or [0] * 12
            idx = start_date.month
            month_target = int(mt[idx - 1]) if 1 <= idx <= 12 else 0
            # 月度计数谓词逐字模仿 calc.py:253-258
            month_count = sum(
                1 for p in persons_with_synthetic
                if rule_matches(p, rule_dict)
                and p.get('counted')
                and p.get('status') in _COUNTED_STATUSES
                and _accounting_month(p) == month_label
                and all(p.get(k) == v for k, v in _indicator_filter(dim_name, ind_name).items())
            )

        annual_break = rule.annual_target > 0 and annual_count >= rule.annual_target
        month_break = month_target > 0 and month_count >= month_target

        if not (annual_break or month_break):
            continue

        entry = {
            'code': rule.code,
            'dimension': dim_name,
            'indicator': ind_name,
            'scope': _scope_text(rule),
            'year': rule.year,
            'annualTarget': rule.annual_target,
            'annualActual': annual_count,
            'monthTarget': month_target,
            'monthActual': month_count,
            'strength': rule.strength,
        }

        if rule.strength == '硬约束':
            blocks.append(entry)
        else:
            # 软约束 / 仅提示：放行，仅提示
            warnings.append(entry)

    if blocks:
        lines = [
            f"规则 {b['code']}（{b['dimension']}·{b['indicator']}，{b['scope']}，{b['year']}）："
            f"当前 {b['annualActual']}/{b['annualTarget']} 人（年度）"
            + (f"、{b['monthActual']}/{b['monthTarget']} 人（月度）" if b['monthTarget'] else "")
            for b in blocks
        ]
        msg = '硬约束规则命中，禁止提交：\n' + '\n'.join(lines)
        raise ControlRuleViolation(msg, status_code=400, blocks=blocks, warnings=warnings)

    return {'blocks': blocks, 'warnings': warnings}
