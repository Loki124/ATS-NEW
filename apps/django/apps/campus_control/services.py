"""人员比例管控系统 — 规则服务层。

包含：
  - T03 副本 / 启用校验 / Offer 钩子（copy_rule / validate_rule_unique / toggle_rule /
    validate_offer_against_rules）
  - 业务方法下沉（v2.9 拆分：set_rules_for_dimension / batch_replace_rules /
    replace_rules_with_targets / import_rules_from_xlsx / import_rule_group /
    import_indicators）

设计约束（用户拍板 3 项修订）：
  ① Candidate 扩展 school_tag / major_tag，Offer 钩子实现「性别 + 院校标签 + 专业标签」全维度命中。
  ② 去掉 handling_method；仅 strength（控制强度）单字段驱动：硬约束→阻断；软约束→放行+提示
    （v2.9：原「仅提示」枚举已合并至「软约束」，二者后端处理完全一致）。
  ③ unique_together 含 is_active：启用原规则 + 未启用副本可共存；副本启用冲突由 validate_rule_unique 拦截。

口径铁律：计数 MUST REUSE calc.py 的 _COUNTED_STATUSES / rule_matches / _indicator_filter /
_accounting_month / count_rule，禁止另写一套计数逻辑，避免与 ratio 看板漂移。

为规避 campus_control.views ↔ campus_control.services 循环 import，
views 的 _person_to_dict / _build_person_dim_map / _rule_to_dict 在本模块内惰性 import。
"""
import base64
import logging
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO

from django.db import IntegrityError, transaction

from apps.audit.models import AuditLog

logger = logging.getLogger(__name__)

from .calc import (
    _COUNTED_STATUSES, rule_matches, _indicator_filter, _accounting_month, count_rule,
    _largest_remainder_allocate,
)
from .constants import STRENGTH
from .io_indicator import (
    build_indicator_error_report_workbook, parse_indicator_file, _parse_bool,
)
from .io_xlsx import (
    parse_import_workbook, build_error_report_workbook,
)
from .models import ControlDimension, ControlIndicator, ControlRule, Person
from .serializers import _to_decimal


class ServiceResult:
    """服务层统一返回：(payload, status_code) 配对。

    View 端用法：
        result = services.<业务方法>(...)
        return Response(result.payload, status=result.status_code)
    """

    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code


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


# ─────────────────────────────────────────────────────────────────────────────
#  T03：副本 / 启用校验 / Offer 钩子（既有 5 个公共函数，签名/行为严格保持）
# ─────────────────────────────────────────────────────────────────────────────

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

    v2.10 增量（Q-A10 拍板 — 单一函数内部按 rule.rollover_enabled 切换月目标）：
      - rollover_enabled=False（默认；v2.4 行为）：按 monthTarget 判定（零回归）。
      - rollover_enabled=True：按 monthTarget + monthRollover 判定；开启时 entry 字典
        透传 5 个浮动字段（rollBase / rollActual / rollover / monthRollover /
        monthAvailableTarget）便于未来 P1-8 阻断文案增强（本期仅透传，不消费）。
      - 关闭时 entry 不含上述 5 字段（保持 v2.4 既有 entry schema 不漂移）。

    参数：
      candidate: Candidate 实例（读 gender / school_tag / major_tag）
      position: Position 实例（读 department.name 作为 bu；风险 3：须与 DEPTS 取值对齐）
      level / position_title: offer 的职级 / 职务文本
      start_date: date 或 None（None 时跳过月度判定，仅年度计数）

    返回：{'blocks': [...], 'warnings': [...]}
      命中硬约束 → 抛 ControlRuleViolation(blocks=..., warnings=...)，由调用方转 400/409 回滚。
      仅软约束命中 → 返回 dict（warnings 非空），调用方 logger.warning 放行。
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
        # v2.10：本月浮动相关字段（关闭时全为 0；entry 不含这些字段以保 v2.4 schema 兼容）
        roll_base = roll_actual = rollover = month_rollover = 0
        month_available_target = 0
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
            # v2.10（Q-A10 拍板 — 单一函数内分支）：按 rollover_enabled 切换月可用目标口径
            if getattr(rule, 'rollover_enabled', False):
                roll_base, roll_actual, rollover, month_rollover = compute_rollover_target(
                    rule_dict, persons, today=start_date,
                )
                # month_available_target = monthTarget + rollover（开启时）
                month_available_target = (
                    int(mt[idx - 1]) + month_rollover if 1 <= idx <= 12 else int(mt[idx - 1])
                )
            else:
                # v2.4 行为（零回归）：按 monthTarget 判定
                month_available_target = month_target

        annual_break = rule.annual_target > 0 and annual_count >= rule.annual_target
        month_break = month_available_target > 0 and month_count >= month_available_target

        if not (annual_break or month_break):
            continue

        entry = {
            'code': rule.code,
            'rule_id': rule.id,
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
        # v2.10：开启浮动才透传 5 字段；关闭时 entry 不变（v2.4 schema 零漂移）
        if getattr(rule, 'rollover_enabled', False):
            entry['rollBase'] = roll_base
            entry['rollActual'] = roll_actual
            entry['rollover'] = rollover
            entry['monthRollover'] = month_rollover
            entry['monthAvailableTarget'] = month_available_target

        if rule.strength == '硬约束':
            blocks.append(entry)
        else:
            # 软约束：放行，仅提示（v2.9：原「仅提示」枚举已合并至此，后端处理一致）
            warnings.append(entry)

    if blocks:
        def _month_line(b):
            """v2.10：开启浮动时显示「额定 + 浮动 = 可用」；关闭时回退到 v2.4「额定目标」口径。"""
            target = b.get('monthTarget') or 0
            if 'monthAvailableTarget' in b and b.get('monthAvailableTarget'):
                target = b['monthAvailableTarget']
                roll = b.get('monthRollover') or 0
                base = b.get('monthTarget') or 0
                return f"、{b['monthActual']}/{target} 人（月度：额定 {base} + 浮动 {roll} = 可用 {target}）"
            return f"、{b['monthActual']}/{target} 人（月度）" if target else ""

        lines = [
            f"规则 {b['code']}（{b['dimension']}·{b['indicator']}，{b['scope']}，{b['year']}）："
            f"当前 {b['annualActual']}/{b['annualTarget']} 人（年度）"
            + _month_line(b)
            for b in blocks
        ]
        msg = '硬约束规则命中，禁止提交：\n' + '\n'.join(lines)
        raise ControlRuleViolation(msg, status_code=400, blocks=blocks, warnings=warnings)

    return {'blocks': blocks, 'warnings': warnings}


# ─────────────────────────────────────────────────────────────────────────────
#  业务方法下沉（v2.9 拆分）— helpers & 私有工具
# ─────────────────────────────────────────────────────────────────────────────

def _scope_mutex_guard(dimension, year, bu, position, level, exclude_scope=None):
    """「全局 / 指定范围」非对称互斥守卫（set_rules / batch / with_targets / 导入入口共用）。

    同一 (dimension, year) 下不可同时持有「全局」与「指定范围」规则集（否则 calc 重复计数）。
    非对称策略（按产品澄清「只删全局、其他指定范围不动」）：
      - 保存/导入【指定范围】→ 删除该维度年度下的【全局】规则，其余指定范围保留；
      - 保存/导入【全局】→ 若存在其他指定范围规则则【拦截 400】，避免静默清空。

    入参 exclude_scope: (bu, position, level, year) 元组，重定位时排除原 scope。
    返回 None 表示放行（已执行必要的删除）；返回 ServiceResult 表示拦截（携带 status=400）。
    """
    if bu or position or level:
        # 指定范围：删除全局规则（其他指定范围保留）
        ControlRule.objects.filter(
            dimension=dimension, year=year,
            bu='', position='', level='',
        ).delete()
        return None
    # 全局：若存在其他指定范围规则则拦截
    specified_qs = ControlRule.objects.filter(
        dimension=dimension, year=year,
    ).exclude(bu='', position='', level='')
    if exclude_scope is not None:
        ebu, epos, elev, eyear = exclude_scope
        specified_qs = specified_qs.exclude(bu=ebu, position=epos, level=elev, year=eyear)
    if specified_qs.exists():
        return ServiceResult(
            {'success': False, 'detail': '该维度年度下已存在其他指定范围规则集，保存全局会清空这些指定范围，请先删除指定范围或改用指定范围保存。'},
            400,
        )
    return None


def _log_rule_audit(user, action, detail, request=None, entity_id=None):
    """规则类写操作审计（清空/保存维度规则集等）。审计失败不阻断主流程。"""
    try:
        ip = (request.META.get('REMOTE_ADDR') or '') if request else ''
        ua = ((request.META.get('HTTP_USER_AGENT') or '')[:500]) if request else ''
        AuditLog.objects.create(
            user=user,
            action=action,
            entity='ControlRule',
            entity_id=entity_id,
            new_value=detail[:1000],
            ip=ip,
            user_agent=ua,
        )
    except Exception:  # noqa: BLE001 - 审计失败不应阻断主流程
        logger.exception('审计写入失败 entity=ControlRule action=%s entity_id=%s', action, entity_id)


def _log_indicator_audit(user, action, detail, request=None, entity_id=None):
    """指标类写操作审计（导入/导出/模板下载）。审计失败不阻断主流程。"""
    try:
        ip = (request.META.get('REMOTE_ADDR') or '') if request else ''
        ua = ((request.META.get('HTTP_USER_AGENT') or '')[:500]) if request else ''
        AuditLog.objects.create(
            user=user,
            action=action,
            entity='ControlIndicator',
            entity_id=entity_id,
            new_value=detail[:1000],
            ip=ip,
            user_agent=ua,
        )
    except Exception:  # noqa: BLE001 - 审计失败不应阻断主流程
        logger.exception('审计写入失败 entity=ControlIndicator action=%s entity_id=%s', action, entity_id)


def _indicator_error_payload(parse_errors, errors_by_line, original_rows, filename=''):
    """构造失败响应 data：融合错误文本 + xlsx 错误报告（base64）。"""
    errs = list(parse_errors) + [f'第 {ln} 行：{msg}' for ln, msg in sorted(errors_by_line.items())]
    payload = {
        'created': 0, 'updated': 0, 'skipped': 0, 'failed': len(errs),
        'errors': errs, 'error_file': None,
    }
    if original_rows:
        try:
            buf = BytesIO()
            wb = build_indicator_error_report_workbook(original_rows, errors_by_line)
            wb.save(buf)
            payload['error_file'] = base64.b64encode(buf.getvalue()).decode('ascii')
        except Exception as e:  # noqa: BLE001 - 报告生成失败不影响主错误返回
            logger.warning('指标导入错误报告生成失败: %s', e)
            payload['error_file'] = None
    return payload


def _normalize_monthly_targets(raw, annual, indicator_name):
    """校验并返回 12 个月度目标数组。annual 为该指标年度管控人数（由调用方分配好，含最大余数法结果）。"""
    annual = int(annual)
    if raw is None:
        # 未传则均分年度目标
        base = annual // 12
        rem = annual - base * 12
        return [base + (1 if i < rem else 0) for i in range(12)]
    if not isinstance(raw, list) or len(raw) != 12:
        return ServiceResult(
            {'success': False, 'detail': f'指标 {indicator_name} 的 monthly_targets 须为长度 12 的数组'},
            400,
        )
    try:
        monthly = [int(v) for v in raw]
    except (TypeError, ValueError):
        return ServiceResult(
            {'success': False, 'detail': f'指标 {indicator_name} 的 monthly_targets 每项须为整数'},
            400,
        )
    if any(v < 0 for v in monthly):
        return ServiceResult(
            {'success': False, 'detail': f'指标 {indicator_name} 的月度目标不能为负数'},
            400,
        )
    if sum(monthly) != annual:
        return ServiceResult(
            {
                'success': False,
                'detail': (
                    f'指标 {indicator_name} 的 12 个月度目标之和({sum(monthly)})'
                    f'须等于年度目标({annual})'
                ),
            },
            400,
        )
    return monthly


# ─────────────────────────────────────────────────────────────────────────────
#  业务方法下沉（v2.9 拆分）— 公共入口
# ─────────────────────────────────────────────────────────────────────────────

def set_rules_for_dimension(user, dimension, payload, request=None):
    """原子替换某 (bu, position, level, dimension, year) 下的全部规则（业务层 1:1 移植自 ControlDimensionViewSet.set_rules）。

    与 /rules/batch/ 同源逻辑：硬校验「目标占比加和 == 100%」，不等于 100% 直接 400；
    通过则事务内删除旧规则并重建。

    入参 payload: {
      bu, position, level, year,
      total_target?,  // 维度年度管控人数：各指标 annualTarget 加和须 == 此值，否则 400（人数加和硬拦）
      rules: [{indicator, target, strength, annual_target?, monthly_targets?}],
    }
      - rules 为空数组 [] → 显式清空该 (适用范围, 维度, 年度) 规则集（跳过 100% 校验与互斥守卫，写审计）。
      - 未出现在 rules 中的指标即视为删除（原子替换语义）。
      - target 为 0~1 小数；strength ∈ STRENGTH。
      - 年度人数 annual_target 与 12 个月度 monthly_targets **成对可选**：
        · 两者都未传 → 从旧规则继承（调整占比不丢人数目标）。
        · 两者都传 → 用前端传入的，并校验 monthly_targets 是长度 12 的非负整数数组，
                   且 monthly_targets 之和 = annual_target（任一不满足 400）。
        · 仅传其中一个 → 400（避免数据不一致）。
      - 若传入 total_target，则 Σ(各规则 annual_target) 须 == total_target，否则 400（人数加和硬拦）。

    返回 ServiceResult：成功 200 + {success: True, data: {saved: N}}，失败 400 + 错误 detail。
    """
    bu = payload.get('bu', '') or ''
    position = payload.get('position', '') or ''
    level = payload.get('level', '') or ''
    year_in = payload.get('year')
    rules_in = payload.get('rules')
    total_target_in = payload.get('total_target')

    try:
        year = int(year_in)
    except (TypeError, ValueError):
        return ServiceResult({'success': False, 'detail': 'year 必填且为整数'}, 400)
    if not isinstance(rules_in, list):
        return ServiceResult({'success': False, 'detail': 'rules 须为数组'}, 400)

    # ---- G5 清空分支：空 rules 数组 = 显式清空该 (适用范围, 维度, 年度) 规则集 ----
    if rules_in == []:
        original_in = payload.get('original')
        obu = opos = olev = ''
        oyear = year
        if isinstance(original_in, dict):
            obu = original_in.get('bu', '') or ''
            opos = original_in.get('position', '') or ''
            olev = original_in.get('level', '') or ''
            try:
                oyear = int(original_in.get('year', year))
            except (TypeError, ValueError):
                return ServiceResult({'success': False, 'detail': 'original.year 须为整数'}, 400)
        if (obu or opos or olev) and (obu != bu or opos != position or olev != level or oyear != year):
            ControlRule.objects.filter(
                bu=obu, position=opos, level=olev, dimension=dimension, year=oyear
            ).delete()
        deleted = ControlRule.objects.filter(
            bu=bu, position=position, level=level, dimension=dimension, year=year
        ).delete()
        _log_rule_audit(
            user, 'DELETE',
            f'清空维度「{dimension.name}」{year}年 适用范围[{bu}/{position}/{level}] 规则集（{deleted[0]} 条）',
            request=request,
        )
        return ServiceResult({'success': True, 'data': {'saved': 0, 'cleared': True}}, 200)

    total = Decimal('0')
    prepared = []
    seen = set()
    existing_by_ind = {
        r.indicator_id: r
        for r in ControlRule.objects.filter(
            bu=bu, position=position, level=level, dimension=dimension, year=year
        )
    }
    for r in rules_in:
        if not isinstance(r, dict):
            return ServiceResult({'success': False, 'detail': 'rules 项须为对象'}, 400)
        indicator_id = r.get('indicator')
        if indicator_id in seen:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator_id} 重复提交'}, 400)
        seen.add(indicator_id)
        indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension.id).first()
        if not indicator:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, 400)
        target = _to_decimal(r.get('target'))
        strength = r.get('strength', '硬约束')
        if target is None:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 目标占比必填且为数值'}, 400)
        if not (Decimal('0') <= target <= Decimal('1')):
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 目标占比须满足 0<=目标<=1'}, 400)
        if strength not in STRENGTH:
            return ServiceResult({'success': False, 'detail': f'控制强度非法：{strength}'}, 400)

        # 年度/月度目标解析（成对可选）
        # 注意：djangorestframework-camel-case parser 已把前端 camelCase 转换为 snake_case，
        # 后端需用 snake_case 读取（annual_target / monthly_targets）。
        annual_in = r.get('annual_target', None)
        monthly_in = r.get('monthly_targets', None)
        if (annual_in is None) != (monthly_in is None):
            return ServiceResult({
                'success': False,
                'detail': f'指标 {indicator.name} 的 annual_target 与 monthly_targets 必须同时传入或不传',
            }, 400)
        if annual_in is None:
            # 从旧规则继承
            old = existing_by_ind.get(indicator.id)
            annual_target = int(old.annual_target) if old else 0
            if old and isinstance(old.monthly_targets, (list, tuple)):
                monthly_targets = [int(v) for v in old.monthly_targets]
            else:
                monthly_targets = [0] * 12
        else:
            # 前端传入，做严格校验
            try:
                annual_target = int(annual_in)
            except (TypeError, ValueError):
                return ServiceResult({
                    'success': False,
                    'detail': f'指标 {indicator.name} 的 annual_target 须为整数',
                }, 400)
            if annual_target < 0:
                return ServiceResult({
                    'success': False,
                    'detail': f'指标 {indicator.name} 的 annual_target 不能为负数',
                }, 400)
            if not isinstance(monthly_in, list) or len(monthly_in) != 12:
                return ServiceResult({
                    'success': False,
                    'detail': f'指标 {indicator.name} 的 monthly_targets 须为长度 12 的数组',
                }, 400)
            try:
                monthly_targets = [int(v) for v in monthly_in]
            except (TypeError, ValueError):
                return ServiceResult({
                    'success': False,
                    'detail': f'指标 {indicator.name} 的 monthly_targets 每项须为整数',
                }, 400)
            if any(v < 0 for v in monthly_targets):
                return ServiceResult({
                    'success': False,
                    'detail': f'指标 {indicator.name} 的 monthly_targets 不能为负数',
                }, 400)
            if sum(monthly_targets) != annual_target:
                return ServiceResult({
                    'success': False,
                    'detail': (
                        f'指标 {indicator.name} 的 12 个月度之和({sum(monthly_targets)})'
                        f'须等于 annual_target({annual_target})'
                    ),
                }, 400)

        total += target
        prepared.append((indicator, target, strength, annual_target, monthly_targets))

    # v2.9：删除「占比加和须=100%」校验（扁平模型下每条规则 target=1.0）

    # ---- G7-② 年度人数加和硬拦 ----
    # 前端传入 totalTarget 时，Σ(各规则 annual_target) 必须 == totalTarget，否则 400（不允许加和不一致的脏数据入库）。
    if total_target_in is not None:
        try:
            total_target_val = int(total_target_in)
        except (TypeError, ValueError):
            return ServiceResult({'success': False, 'detail': 'totalTarget 须为非负整数'}, 400)
        if total_target_val < 0:
            return ServiceResult({'success': False, 'detail': 'totalTarget 不能为负数'}, 400)
        annual_sum = sum(p[3] for p in prepared)
        if annual_sum != total_target_val:
            return ServiceResult({
                'success': False,
                'detail': (
                    f'各指标年度管控人数加和({annual_sum})'
                    f'须等于「维度年度管控人数」({total_target_val})'
                ),
            }, 400)

    # ---- 「重定位」支持：编辑态下适用范围被改 ----
    # original 为编辑打开时的原适用范围快照；若与当前 scope 不同，则删除原 scope 规则集、在新 scope 重建。
    # 目标 scope 已存在规则集 → 冲突拦截（避免覆盖）。
    relocate = False
    obu = opos = olev = ''
    oyear = year
    original_in = payload.get('original')
    if isinstance(original_in, dict):
        obu = original_in.get('bu', '') or ''
        opos = original_in.get('position', '') or ''
        olev = original_in.get('level', '') or ''
        try:
            oyear = int(original_in.get('year', year))
        except (TypeError, ValueError):
            return ServiceResult({'success': False, 'detail': 'original.year 须为整数'}, 400)
        relocate = (obu != bu or opos != position or olev != level or oyear != year)

    # ---- 「全局 / 指定范围」互斥（非对称，守卫统一处理） ----
    block = _scope_mutex_guard(
        dimension, year, bu, position, level,
        exclude_scope=(obu, opos, olev, oyear) if relocate else None,
    )
    if block is not None:
        return block

    with transaction.atomic():
        if relocate:
            # 重定位：先删原 scope 规则集（同事务原子，失败整体回滚）
            ControlRule.objects.filter(
                bu=obu, position=opos, level=olev, dimension=dimension, year=oyear
            ).delete()
        ControlRule.objects.filter(
            bu=bu, position=position, level=level, dimension=dimension, year=year
        ).delete()
        for indicator, target, strength, annual_target, monthly_targets in prepared:
            ControlRule.objects.create(
                bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                year=year, target=target, strength=strength,
                annual_target=annual_target, monthly_targets=monthly_targets,
                created_by=user, updated_by=user,
            )
    return ServiceResult({'success': True, 'data': {'saved': len(prepared)}}, 200)


def batch_replace_rules(user, payload, request=None):
    """批量保存某 (bu, position, level, dimension, year) 下全部规则（原子替换）。

    硬校验「目标占比加和 == 100%」，不等于 100% 直接 400；通过则事务内删除旧规则重建。
    v2.4：取消上下限；人数目标（annual_target / monthly_targets）默认 0，可在规则中单独编辑。
    """
    bu = payload.get('bu', '') or ''
    position = payload.get('position', '') or ''
    level = payload.get('level', '') or ''
    dimension_id = payload.get('dimension')
    year = int(payload.get('year') or 2026)
    rules = payload.get('rules')
    if not dimension_id:
        return ServiceResult({'success': False, 'detail': '缺少 dimension 参数'}, 400)
    dimension = ControlDimension.objects.filter(pk=dimension_id).first()
    if not dimension:
        return ServiceResult({'success': False, 'detail': '维度不存在'}, 404)
    if not isinstance(rules, list) or not rules:
        return ServiceResult({'success': False, 'detail': 'rules 不能为空'}, 400)

    total = Decimal('0')
    prepared = []
    seen = set()
    for r in rules:
        if not isinstance(r, dict):
            return ServiceResult({'success': False, 'detail': 'rules 项须为对象'}, 400)
        indicator_id = r.get('indicator')
        indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension_id).first()
        if not indicator:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, 400)
        if indicator_id in seen:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 重复提交'}, 400)
        target = _to_decimal(r.get('target'))
        strength = r.get('strength', '硬约束')
        if target is None:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 目标占比必填且为数值'}, 400)
        if not (Decimal('0') <= target <= Decimal('1')):
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 目标占比须满足 0<=目标<=1'}, 400)
        if strength not in STRENGTH:
            return ServiceResult({'success': False, 'detail': f'控制强度非法：{strength}'}, 400)
        total += target
        prepared.append((indicator, target, strength))
        seen.add(indicator_id)

    # v2.9：删除「占比加和须=100%」校验（扁平模型下每条规则 target=1.0，无需加和约束）

    # ---- 「全局 / 指定范围」互斥（非对称，与 set_rules 一致） ----
    block = _scope_mutex_guard(dimension, year, bu, position, level)
    if block is not None:
        return block

    with transaction.atomic():
        ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension, year=year).delete()
        for indicator, target, strength in prepared:
            ControlRule.objects.create(
                bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                year=year, target=target, strength=strength,
                created_by=user, updated_by=user,
            )
    return ServiceResult({'success': True, 'data': {'saved': len(prepared)}}, 200)


def replace_rules_with_targets(user, payload, request=None):
    """批量配置规则 + 人数目标（一次性原子操作）。

    入参: { bu, position, level, dimension, year, totalTarget,
             rules: [{indicator, target, strength, monthly_targets?}] }
    行为（v2.4）：取消上下限；人数目标直接承载于规则上。
      - 校验 100% 加和 + 0<=target<=1 + indicator∈dimension
      - 事务内: 删除该(适用范围, 维度, 年度)旧规则 → 创建新规则
      - 每条规则 annual_target 由「最大余数法」按 totalTarget×target 精确分配（保证 Σannual == totalTarget，杜绝 round 加和漂移）
      - monthly_targets 优先取前端传入；未传则按年度目标均分 12 个月
      - 校验 monthly_targets 为长度 12 的非负整数数组且加和=annual_target
    """
    bu = payload.get('bu', '') or ''
    position = payload.get('position', '') or ''
    level = payload.get('level', '') or ''
    dimension_id = payload.get('dimension')
    year_in = payload.get('year')
    total_target_in = payload.get('total_target')
    rules_in = payload.get('rules')

    if not dimension_id:
        return ServiceResult({'success': False, 'detail': '缺少 dimension 参数'}, 400)
    dimension = ControlDimension.objects.filter(pk=dimension_id).first()
    if not dimension:
        return ServiceResult({'success': False, 'detail': '维度不存在'}, 404)
    try:
        year = int(year_in)
    except (TypeError, ValueError):
        return ServiceResult({'success': False, 'detail': 'year 必填且为整数'}, 400)
    try:
        total_target = int(total_target_in)
    except (TypeError, ValueError):
        return ServiceResult({'success': False, 'detail': 'totalTarget 必填且为非负整数'}, 400)
    if total_target < 0:
        return ServiceResult({'success': False, 'detail': 'totalTarget 不能为负数'}, 400)
    if not isinstance(rules_in, list) or not rules_in:
        return ServiceResult({'success': False, 'detail': 'rules 不能为空'}, 400)

    total = Decimal('0')
    prepared = []   # (indicator, target, strength, raw_monthly)
    weights = []    # 各指标占比（和须=1），用于最大余数法分配 annual_target
    seen = set()
    for r in rules_in:
        if not isinstance(r, dict):
            return ServiceResult({'success': False, 'detail': 'rules 项须为对象'}, 400)
        indicator_id = r.get('indicator')
        if indicator_id in seen:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator_id} 重复提交'}, 400)
        seen.add(indicator_id)
        indicator = ControlIndicator.objects.filter(pk=indicator_id, dimension_id=dimension_id).first()
        if not indicator:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator_id} 不属于该维度'}, 400)
        target = _to_decimal(r.get('target'))
        strength = r.get('strength', '硬约束')
        if target is None:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 目标占比必填且为数值'}, 400)
        if not (Decimal('0') <= target <= Decimal('1')):
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 目标占比须满足 0<=目标<=1'}, 400)
        if strength not in STRENGTH:
            return ServiceResult({'success': False, 'detail': f'指标 {indicator.name} 控制强度非法'}, 400)
        total += target
        prepared.append((indicator, target, strength, r.get('monthly_targets')))
        weights.append(float(target))

    # v2.9：删除「占比加和须=100%」校验（扁平模型下每条规则 target=1.0）

    # 最大余数法：把维度总人数精确分配为各指标 annual_target，保证 Σannual == total_target
    annuals = _largest_remainder_allocate(total_target, weights)

    # 逐指标校验/归一化月度目标（annual 已分配好）
    monthly_by_idx = []
    for i, (indicator, target, strength, raw_monthly) in enumerate(prepared):
        monthly = _normalize_monthly_targets(raw_monthly, annuals[i], indicator.name)
        if isinstance(monthly, ServiceResult):
            return monthly
        monthly_by_idx.append(monthly)

    # ---- 「全局 / 指定范围」互斥（非对称，与 set_rules 一致） ----
    block = _scope_mutex_guard(dimension, year, bu, position, level)
    if block is not None:
        return block

    with transaction.atomic():
        # 删除该 (适用范围, 维度, 年度) 旧规则
        ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension, year=year).delete()
        for i, (indicator, target, strength, _raw) in enumerate(prepared):
            ControlRule.objects.create(
                bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                year=year, target=target, strength=strength,
                annual_target=annuals[i], monthly_targets=monthly_by_idx[i],
                created_by=user, updated_by=user,
            )
    return ServiceResult({
        'success': True,
        'data': {'saved': len(prepared), 'totalTarget': total_target, 'year': year},
    }, 200)


def import_rules_from_xlsx(user, file_obj, filename='', request=None):
    """导入 xlsx 规则文件：按 (适用范围, 维度, 年度) 分组，校验 100% 与月度一致性，事务原子替换。

    复用 with_targets 的校验语义；每组独立事务，任一组失败则该组回滚并计入错误。
    返回 { success, data: { groups, saved_rules, errors } }。
    """
    if not file_obj:
        return ServiceResult(
            {'success': False, 'data': {'groups': 0, 'saved_rules': 0, 'errors': ['缺少 file 文件字段'], 'error_file': None}},
            400,
        )
    if not (filename or '').lower().endswith(('.xlsx', '.xlsm')):
        return ServiceResult(
            {'success': False, 'data': {'groups': 0, 'saved_rules': 0, 'errors': ['仅支持 .xlsx 文件'], 'error_file': None}},
            400,
        )

    try:
        groups, parse_errors, original_rows, errors_by_line = parse_import_workbook(file_obj)
    except Exception as e:  # noqa: BLE001 - 解析异常统一返回
        logger.warning('规则集 xlsx 解析失败 filename=%s err=%s', filename, e)
        return ServiceResult(
            {'success': False, 'data': {'groups': 0, 'saved_rules': 0, 'errors': [f'文件解析失败：{e}'], 'error_file': None}},
            400,
        )

    def _error_payload(extra_errors):
        """构造失败响应：除 errors 文本列表外，附融合后的错误报告 xlsx（base64）。"""
        errs = list(parse_errors) + list(extra_errors)
        payload = {'groups': 0, 'saved_rules': 0, 'errors': errs, 'error_file': None}
        if original_rows:
            try:
                buf = BytesIO()
                wb = build_error_report_workbook(original_rows, errors_by_line)
                wb.save(buf)
                payload['error_file'] = base64.b64encode(buf.getvalue()).decode('ascii')
            except Exception as e:  # noqa: BLE001 - 报告生成失败不影响主错误返回
                logger.warning('规则集导入错误报告生成失败: %s', e)
                payload['error_file'] = None
        return payload

    if parse_errors:
        return ServiceResult({
            'success': False,
            'data': _error_payload([]),
        }, 400)

    if not groups:
        return ServiceResult({
            'success': False,
            'data': _error_payload(['文件中未解析到任何有效规则行']),
        }, 400)

    saved_rules = 0
    group_errors = []
    for g in groups:
        ok, msg, n = import_rule_group(g, user)
        if not ok:
            group_errors.append(msg)
        else:
            saved_rules += n

    if group_errors:
        return ServiceResult({
            'success': False,
            'data': _error_payload(group_errors),
        }, 400)

    return ServiceResult({
        'success': True,
        'data': {'groups': len(groups), 'saved_rules': saved_rules, 'errors': []},
    }, 200)


def import_rule_group(group, user):
    """导入单个 (适用范围, 维度, 年度) 组，事务原子替换。v2.9 扁平模型：每组 1 条规则。

    返回 (ok, msg, saved_count)。
    """
    bu = group.get('bu', '') or ''
    position = group.get('position', '') or ''
    level = group.get('level', '') or ''
    dimension_name = group.get('dimension')
    year = int(group.get('year') or 2026)
    rules_in = group.get('rules') or []

    dimension = ControlDimension.objects.filter(name=dimension_name).first()
    if not dimension:
        return False, f'组[{dimension_name}]：维度不存在（请检查导入文件中的维度名是否与系统启用维度一致）', 0

    prepared = []
    seen = set()
    for r in rules_in:
        indicator_name = r.get('indicator')
        if indicator_name in seen:
            return False, f'组[{dimension_name}]：指标「{indicator_name}」在同一适用范围+维度+年度下重复', 0
        seen.add(indicator_name)
        indicator = ControlIndicator.objects.filter(name=indicator_name, dimension=dimension, is_active=True).first()
        if not indicator:
            return False, f'组[{dimension_name}]：指标「{indicator_name}」不属于该维度或未启用', 0
        # v2.9 扁平模型：target 恒 1.0，不再校验占比范围
        strength = r.get('strength', '硬约束')
        if strength not in STRENGTH:
            return False, f'组[{dimension_name}]：控制强度「{strength}」非法（须为 硬约束/软约束）', 0
        monthly = r.get('monthly_targets') or [0] * 12
        if len(monthly) != 12:
            return False, f'组[{dimension_name}]：指标「{indicator_name}」月度目标须为长度 12', 0
        if any(v < 0 for v in monthly):
            return False, f'组[{dimension_name}]：指标「{indicator_name}」月度目标不能为负', 0
        prepared.append((indicator, strength, monthly))

    # ---- 「全局 / 指定范围」互斥（非对称，与 set_rules 一致） ----
    block = _scope_mutex_guard(dimension, year, bu, position, level)
    if block is not None:
        return False, block.payload.get('detail', '适用范围互斥冲突'), 0

    with transaction.atomic():
        ControlRule.objects.filter(bu=bu, position=position, level=level, dimension=dimension, year=year).delete()
        for indicator, strength, monthly in prepared:
            # v2.9：扁平模型 annual = 行级年度目标（不再按占比 * totalTarget 拆分）
            annual = int(rules_in[0].get('annual_target', 0) or 0)
            ControlRule.objects.create(
                bu=bu, position=position, level=level, dimension=dimension, indicator=indicator,
                year=year, target=Decimal('1.0'), strength=strength,
                annual_target=annual, monthly_targets=monthly,
                created_by=user, updated_by=user,
            )
    return True, '', len(prepared)


def import_indicators(user, file_obj, mode, filename='', request=None):
    """批量导入指标：数据校验 + 重复项处理（mode=skip|update|error）。

    校验：维度须存在；指标名称非空且 ≤32；是否启用须可解析；文件内同 (维度,指标名称) 不可重复。
    与库内重复按 mode 处理：skip=跳过 / update=更新 is_active / error=整批拒绝（原子回滚）。
    任一硬校验错误 → 整体 400 并附错误报告（xlsx，base64）。
    """
    if not file_obj:
        return ServiceResult({'success': False, 'detail': '缺少 file 文件字段'}, 400)
    mode = (mode or 'skip').strip().lower()
    if mode not in ('skip', 'update', 'error'):
        return ServiceResult({'success': False, 'detail': 'mode 仅支持 skip / update / error'}, 400)

    rows, parse_errors, original_rows, errors_by_line = parse_indicator_file(file_obj)

    if parse_errors:
        return ServiceResult(
            {'success': False, 'data': _indicator_error_payload(parse_errors, {}, [], filename)},
            400,
        )
    if not rows:
        return ServiceResult(
            {'success': False, 'data': _indicator_error_payload(['文件中未解析到任何有效指标行'], {}, [], filename)},
            400,
        )

    # 预构建维度映射，避免逐行查库
    dim_map = {d.name: d for d in ControlDimension.objects.all()}

    seen_in_file = {}
    for rec in rows:
        line = rec['line']
        dim_name = rec['dimension_name']
        name = rec['name']
        dimension = dim_map.get(dim_name)
        if dimension is None:
            errors_by_line[line] = f'维度「{dim_name}」不存在'
            continue
        if not name:
            errors_by_line[line] = '指标名称为空'
            continue
        if len(name) > 32:
            errors_by_line[line] = f'指标名称过长（须 ≤32，当前 {len(name)}）'
            continue
        is_active = _parse_bool(rec['is_active_raw'])
        if is_active is None:
            errors_by_line[line] = f'是否启用非法：{rec["is_active_raw"]!r}（填写 是/否/true/false/1/0）'
            continue
        key = (dimension.id, name)
        if key in seen_in_file:
            errors_by_line[line] = f'与第 {seen_in_file[key]} 行重复（同维度同指标名称）'
            continue
        seen_in_file[key] = line
        existing = ControlIndicator.objects.filter(dimension=dimension, name=name).first()
        if existing and mode == 'error':
            errors_by_line[line] = f'指标「{dim_name}/{name}」已存在，mode=error 拒绝导入'

    if errors_by_line:
        return ServiceResult(
            {'success': False, 'data': _indicator_error_payload([], errors_by_line, original_rows, filename)},
            400,
        )

    # 第二遍：写库（此阶段已无硬错误）
    created = updated = skipped = 0
    with transaction.atomic():
        for rec in rows:
            dimension = dim_map[rec['dimension_name']]
            name = rec['name']
            is_active = _parse_bool(rec['is_active_raw'])
            existing = ControlIndicator.objects.filter(dimension=dimension, name=name).first()
            if existing:
                if mode == 'skip':
                    skipped += 1
                    continue
                existing.is_active = is_active
                existing.updated_by = user
                existing.save(update_fields=['is_active', 'updated_by'])
                updated += 1
                continue
            ControlIndicator.objects.create(
                dimension=dimension, name=name, is_active=is_active,
                created_by=user, updated_by=user,
            )
            created += 1

    action = 'CREATE' if created else ('UPDATE' if updated else 'READ')
    detail = f'导入指标完成：新建 {created} / 更新 {updated} / 跳过 {skipped}（mode={mode}）'
    _log_indicator_audit(user, action, detail, request=request)
    return ServiceResult({
        'success': True,
        'data': {'created': created, 'updated': updated, 'skipped': skipped, 'failed': 0, 'errors': []},
    }, 200)
