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
只是把条件纳入指标模板治理体系（EXP-5 失效检测 + LIFE-2 禁用/删除披露）。

⚠️「求值结果不变」的适用边界（务必看清，不要过度宣称）
------------------------------------------------------
上述「同源 ⇒ 求值结果不变」**仅对标准点路径形态成立**：裸路径 field 与 AtomicMetric.source_path
是同一个点路径（candidate.age <-> candidate.age），取值走同一 FieldResolverRegistry，
故迁移前后 actual 必然相同、比较结果必然相同。

**legacy 大写常量形态（DEMAND_LEVEL 等）属尽力映射，不保证同源等价**，必须人工核对：
  - 迁移前：entry_condition/services.py 的裸路径取值表按 legacy 常量名取值（如 'DEMAND_LEVEL'
    走 getattr(demand, 'demand_level', None)）。Demand 模型只有 level 字段、没有 demand_level，
    因此该条件迁移前 actual **恒为 None**，EQ 任意值恒 False。
  - 迁移后：走 demand.level，取 Demand.level —— 真实值域与配置值（如 '1'/'3'）未必对得上，
    前后都为 False 可能是**碰巧**，并非语义等价。
  - 结论：legacy 形态只做命名规范化 + 查表命中，**不承诺求值结果不变**；执行 --apply 前
    必须人工核对每条 legacy 项的语义与配置值是否匹配。

运算符白名单（硬性不变量，禁产出不可求值条件）
---------------------------------------------
MetricEngine 求值时会**强制校验** operator ∈ template.operators（metric_engine.py:126-130 批量 /
:337-344 单条），不在白名单直接返回 error='模板不支持该运算符' + pass=False，而 entry_condition
把 error 降级为 passed=False（services.py:375-380）→ **候选人被静默拦截**。
因此本命令绝不产出「operator 不在目标模板 operators 内」的迁移结果。

目标模板解析策略（最小侵入，按序；**严禁「全集 operators」兜底**）
------------------------------------------------------------------
  1. **复用兼容模板**：指向同一 AtomicMetric 且 operator 已在其 operators 内的启用模板。
  2. **并入缺失的 1 个 operator**（无兼容模板时的首选）：复用指向该 AtomicMetric 的既有启用
     模板，只把「缺失的那一个 operator」**追加**进其 operators，**不新建重复模板**、
     **不开放无关算子**。
     ⚠️ 为什么**不能**新建「全集 operators（UnifiedOperator.values 14 项）」模板：
     迁移 0018 刻意把 `需求级别` 模板的 operators 定为
     ['IS_EMPTY','IS_NOT_EMPTY','IN','NOT_IN'] 安全集，这是有意的业务约束；而
     demand.level 是 **CharField 职级**。开全集（含 GT / BETWEEN / REGEX_MATCH…）
     会让用户配出「职级 > 5」这类无意义条件，求值因字符串比较而**静默 False** ——
     这是另一种「假及格」（配置能存、求值恒 False），比重复模板命名危险得多。
     故全集兜底已**彻底废弃**。

「类型 × 算子」分级门禁（E-2，--apply 前置门禁）
---------------------------------------------
上述「只并入缺失的那 1 个算子」把风险幅度从 14 降到 1，但**风险类别没变**：仍然是
「由数据驱动地把一个算子写进全局共享模板白名单」。dev 那批待迁项恰好只需要 EQ，
所以风险没有实际发生 —— 那是**数据集运气，不是代码保证**。若某批待迁项的 operator
是数值/区间算子（GT / GTE / LT / LTE / BETWEEN）而目标字段是字符串类
（如 demand.level = CharField 职级，data_type='string'），并入会把「职级 > 5」
变成可配配置 → 字符串比较 → **求值静默 False**（传导链路不变：operators 经
apps/process/views.py:958 透传给前端运算符下拉）。

故在**并入 / 新建白名单之前**再加一道分级校验（_operator_merge_policy）：
  - 字符串类 data_type（MetricDataType.STRING）：只允许**字符串安全算子**并入
    （EQ / NEQ / IN / NOT_IN / IS_EMPTY / IS_NOT_EMPTY / CONTAINS / NOT_CONTAINS /
    REGEX_MATCH）；数值比较算子（GT / GTE / LT / LTE）与区间算子（BETWEEN）
    一律 **不允许 → SKIP + 报告**（禁假绿，绝不硬造 data_type / 模板）。
  - 非字符串类（number / date / boolean…）：**不做任何限制**，行为完全不变。
  - 门禁只作用于「要把算子**写进**白名单」的两条路径（并入既有模板 / 新建模板）；
    「复用本就兼容的模板」不改任何配置，不受门禁影响（判定语义不变）。
  - dry-run 计划分支 `_plan_template_note` 与 --apply 分支 `_resolve_template`
    共用同一分级函数，故 dry-run 与 --apply 口径**严格一致**：
    dry-run 计划文案同步体现 `[SKIP 运算符 GT 不适用于 STRING 字段 demand.level]`。
  3. **新建最小算子模板**：仅有既有模板可改（并入失败）或根本没有既有模板时才新建，
     operators **只含本条实际需要的那 1 个算子**（绝不是 UnifiedOperator 全集）；
     name 用候选名序列（am.name → am.name (LIFE-3) → am.name (LIFE-3 <6位随机>)），
     name 唯一冲突时逐级重试。
  4. operator 不是合法 UnifiedOperator 取值 → SKIP + 报告；运算符为空且无既有模板
     （新建会得到空白名单模板 = 不可求值）→ SKIP + 报告。
  5. 以上都失败 → SKIP + 报告（禁假绿底线不变）。

「并入既有模板 operators」对既有引用条件的影响（已论证 + 测试锁定）
------------------------------------------------------------------
operators 是**启用算子白名单**（metric_engine 只做 `operator ∈ template.operators` 的
成员判断）。追加只会**放宽**白名单：既有条件原本允许的运算符**全部保留**（append-only，
绝不删改），既有条件既不会因白名单缩小而失效，也不会改变任何一条既有条件的
operator / value / 取值路径（本命令只改 operators 字段本身）。
故「并入」对既有引用该模板的条件**无破坏性影响**，只是让该模板多支持一个运算符。
（回归测试 test_merge_preserves_existing_operators_and_conditions 锁定此结论。）

并入的可审计性（E-1，纯输出/报告层）
----------------------------------
并入是对**全局共享实体**（MetricTemplate）的永久性配置面变更：operators 经
apps/process/views.py:958 `'operators': list(tpl.operators or [])` 透传给前端运算符下拉，
而本命令**不可回滚**。故 --apply 输出必须能回答「改了哪些模板、并入哪个算子、
operators 从几个变到几个」，且 dry-run 要给出同一份**计划**清单（口径一致）：
  - 单条输出三态可辨：`[模板 X]`（复用本就兼容）/
    `[并入 +EQ 到既有模板 X（operators 4→5：[..] → [..]）]`（并入放宽）/
    `[新建模板 X operators=[EQ]]`（新建最小算子模板）。
  - 报告末尾新增「已放宽既有模板白名单」汇总（dry-run 为「将放宽」），
    按模板归并：同一模板被并入多个算子时合并显示，0 个也显式打印以证无放宽。
该改动只在**写库成功后登记**（_merge_operator_into_template / _create_minimal_template）
或 dry-run 预测并入时登记（_plan_template_note），**不参与任何迁移判定与写入决策**。

可靠性约束（硬纪律，必须遵守）
-----------------------------
  - 绝不硬造 data_type：只有按 source_path 查到 status='enabled' 的 AtomicMetric 时才迁移；
    查不到则 SKIP 并在报告中列出该路径。不猜测/创建带错误 data_type 的 AtomicMetric
    （那会伪造、导致求值错误 = 假绿）。
  - 零 schema 变更：不新增/修改任何 model 字段、不新增 migration 文件。
    ConditionItem.condition_type 的 choices 已含 'METRIC'（P0 已加），直接存 'METRIC' 合法。
  - 零新增依赖。
  - 真实可靠：dry-run 默认不写库；--apply 才写。

legacy 命名兼容（修复：明明有 enabled AtomicMetric 却误判 SKIP）
---------------------------------------------------------------
裸路径 field 在真实库里存在两种命名风格：
  1. 标准点路径：candidate.age / demand.level（小写、含点）
  2. legacy 大写常量：DEMAND_LEVEL / CANDIDATE_WORK_YEARS（全大写、下划线、无点）
原先直接把 ci.field 当 source_path 精确查，只覆盖风格 1，导致风格 2 明明有对应
enabled AtomicMetric 也被判「无」而 SKIP（本可迁移的数据一条没迁）。
现统一走 _resolve_atomic_metric()：**精确匹配优先，legacy 规范化仅作兜底**
（见 _normalize_legacy_path）。规范化只作用于「全大写 + 含下划线 + 无点」的 field，
标准点路径与已迁移的模板 id 完全不受影响；查不到依旧 SKIP，绝不硬造。

⚠️ 兜底映射命中的项**仍需人工核对语义与配置值**（理由见上文「求值结果不变的适用边界」）：
legacy 常量迁移前的实际取值链路与 demand.level 未必同源，命中只代表「存在同名的标准点路径
AtomicMetric」，不代表迁移前后求值结果一致。--apply 输出会为每条命中项打印
`[经规范化匹配 X -> y]` 兜底提示，并在报告里汇总命中条数，保证事后可审计。

求值权威路径（已核实，无需再查）
-------------------------------
apps/entry_condition/services.py:270 与 :280 的求值循环直接
rule.items.filter(deleted_at__isnull=True)（ORM ConditionItem），**不读**
ProcessStageLink.entry_rule_expression 缓存。所以改 ConditionItem 即生效于准入。
entry_rule_expression 仅是展示缓存，本命令 best-effort 重建它（失败仅 warn 不致命）。
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Tuple

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction

from apps.entry_condition.models import (
    ConditionFieldType,
    ConditionItem,
    EntryConditionRule,
)
from apps.metrics.models import (
    AtomicMetric,
    MetricDataType,
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

# MetricTemplate.name 的 max_length（模型定义 64），新建模板时用于截断候选名
_TEMPLATE_NAME_MAX = 64

# 新建模板时 name 的可辨识后缀（与既有同名模板区分，便于人工回溯来源）
_NEW_TEMPLATE_SUFFIX = ' (LIFE-3)'

# ---------------------------------------------------------------------------
# E-2「类型 × 算子」分级门禁常量
# ---------------------------------------------------------------------------
# 「字符串类」data_type 集合（MetricDataType.STRING）。
# number / date / boolean 均**不受**本门禁限制（行为完全不变）。
# 存**原始 value 字符串**（而非 TextChoices 成员）：集合判等走 hash，
# 用成员本身会踩 Enum 的 hash(_name_) 语义差异，故显式取 .value 固化成 'string'。
_STRING_DATA_TYPES = frozenset({str(MetricDataType.STRING.value)})

# 数值比较算子 + 区间算子：在字符串类字段上求值会退化为字符串比较 →
# 「职级 > 5」这类条件配置能存、求值恒 False = 另一种「假及格」，一律禁止写入白名单。
_NUMERIC_COMPARE_OPERATORS = ('GT', 'GTE', 'LT', 'LTE', 'BETWEEN')

# 字符串类字段允许写入白名单的安全算子（含集合/空值/子串/正则四类字符串语义算子）
_STRING_SAFE_OPERATORS = (
    'EQ', 'NEQ', 'IN', 'NOT_IN', 'IS_EMPTY', 'IS_NOT_EMPTY',
    'CONTAINS', 'NOT_CONTAINS', 'REGEX_MATCH',
)


def _fit_template_name(base: str, suffix: str) -> str:
    """把 base + suffix 拼进 64 字符上限内（超长则截断 base，绝不截断后缀）。"""
    base = base or 'metric'
    if len(base) + len(suffix) <= _TEMPLATE_NAME_MAX:
        return base + suffix
    keep = _TEMPLATE_NAME_MAX - len(suffix)
    if keep <= 0:
        return (base + suffix)[-_TEMPLATE_NAME_MAX:]
    return base[:keep] + suffix


def _format_ops(operators: Any) -> str:
    """把 operators 列表渲染成紧凑可读形式（**仅用于输出/报告，绝不参与任何判定**）。"""
    return '[' + ', '.join(str(op) for op in (operators or [])) + ']'


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


def _normalize_legacy_path(field: Any) -> Any:
    """legacy「大写常量」形态 → 标准点路径形态（仅做命名规范化，绝不猜测语义）。

    真实 legacy 数据存在两种命名风格，本命令原先只认标准点路径一种：
      - 标准点路径：candidate.age / demand.level（小写、含点）
      - legacy 大写常量：DEMAND_LEVEL / CANDIDATE_WORK_YEARS（全大写、下划线、无点）

    仅当 field 严格满足「是字符串 + 无点 + 含下划线 + 全大写」时才规范化：
      把第一个下划线替换为 '.'，整体转小写。
        DEMAND_LEVEL          -> demand.level
        CANDIDATE_WORK_YEARS  -> candidate.work_years
    不满足该形态的 field 一律原样返回（标准点路径、模板 id、小写下划线等），
    保证精确匹配路径与既有行为完全不受影响。

    注意：这只是让「已有对应 enabled AtomicMetric」的项能被匹配到，
    绝不据此外推 data_type 或凭空造指标 —— 查不到仍然 SKIP。
    """
    if not isinstance(field, str) or not field:
        return field
    if '.' in field:
        return field  # 已是点路径形态（或数组下标路径），原样返回
    if '_' not in field:
        return field  # 无下划线，无「下划线 -> 点」可替换
    if not field.isupper():
        return field  # 非全大写常量风格，原样返回
    return field.replace('_', '.', 1).lower()


def _resolve_atomic_metric(field: Any) -> Tuple[AtomicMetric | None, Any]:
    """按 field 解析出「已启用」的 AtomicMetric —— 精确匹配优先，legacy 规范化仅作兜底。

    Args:
        field: ConditionItem.field 或 JSON item 的 field（裸路径或 legacy 大写常量）。

    Returns:
        (am, resolved_path)：
          - am: 命中的 AtomicMetric；为 None 表示查不到，调用方必须 SKIP
                （绝不硬造 data_type / 模板，避免假绿）。
          - resolved_path: 实际用于查询的 source_path。命中时即命中路径；
                未命中时为规范化后的候选路径（可能为原 field），供报告溯源。
    """
    path = field
    am = AtomicMetric.objects.filter(
        source_path=path, status=MetricStatus.ENABLED,
    ).first()
    if am is not None:
        return am, path

    # 兜底：legacy 大写常量风格（DEMAND_LEVEL）→ 标准点路径（demand.level）再查一次
    normalized = _normalize_legacy_path(field)
    if normalized != field:
        am = AtomicMetric.objects.filter(
            source_path=normalized, status=MetricStatus.ENABLED,
        ).first()
        if am is not None:
            return am, normalized
    return None, normalized


def _normalize_data_type(data_type: Any) -> str:
    """把 data_type 归一化成小写字符串（兼容 TextChoices 成员与裸字符串两种形态）。

    MetricDataType 是 Django TextChoices：`getattr(x, 'value', x)` 取到 'string' 等原始值；
    裸字符串（历史脏数据 / JSON 里的值）则原样使用。大小写与首尾空格一律归一。
    """
    value = getattr(data_type, 'value', data_type)
    return str(value or '').strip().lower()


def _is_string_data_type(data_type: Any) -> bool:
    """data_type 是否属「字符串类」（MetricDataType.STRING）。

    只有字符串类受 E-2 门禁限制；number / date / boolean 一律返回 False（行为不变）。
    """
    return _normalize_data_type(data_type) in _STRING_DATA_TYPES


def _operator_merge_policy(data_type: Any, operator: Any) -> Tuple[bool, str]:
    """E-2「类型 × 算子」分级：判断 operator 是否允许**写进**该 data_type 字段的模板白名单。

    为什么要这道门禁
    ----------------
    「只并入缺失的那 1 个算子」把风险幅度从 14 降到 1，但**风险类别没变**：仍是由数据驱动
    地把算子写进全局共享模板白名单（operators 经 apps/process/views.py:958 透传给前端
    运算符下拉）。dev 那批待迁项恰好只需要 EQ 才没出事 —— 那是数据集运气，不是代码保证。
    若待迁项是 GT / BETWEEN 而目标字段是字符串类（demand.level = CharField 职级），
    并入/新建会让「职级 > 5」变成可配配置 → 字符串比较 → **求值静默 False**。

    分级规则
    --------
      - 非字符串类（number / date / boolean…）：**不做任何限制**，一律允许（行为不变）。
      - 字符串类：只允许字符串安全算子（EQ / NEQ / IN / NOT_IN / IS_EMPTY /
        IS_NOT_EMPTY / CONTAINS / NOT_CONTAINS / REGEX_MATCH）；
        数值比较算子（GT / GTE / LT / LTE）与区间算子（BETWEEN）一律**拒绝**。
      - operator 为空：不做判定（交由既有「运算符为空」分支处理，保证行为零变化）。
      - 非法 operator：拒绝（调用方已先做过一次校验，此处为纵深防御）。

    Args:
        data_type: AtomicMetric.data_type（TextChoices 成员或裸字符串）。
        operator: 待写入白名单的运算符。

    Returns:
        (allowed, reason)：
          - allowed=True  → 允许并入/新建；reason 为 ''。
          - allowed=False → 必须 SKIP + 报告；reason 为**不含字段路径**的原因短语，
            由调用方拼上字段路径后打印（保证 dry-run 与 --apply 文案一致）。
    """
    if not operator:
        # 空运算符属既有「运算符为空」分支的语义，本门禁不参与判定（零行为变化）
        return True, ''
    data_type_text = _normalize_data_type(data_type)
    if data_type_text not in _STRING_DATA_TYPES:
        return True, ''  # 非字符串类：不做限制
    operator_text = str(operator).strip()
    if operator_text not in UnifiedOperator.values:
        return False, f'运算符 {operator} 非合法 UnifiedOperator'
    if operator_text in _NUMERIC_COMPARE_OPERATORS:
        return False, f'运算符 {operator_text} 不适用于 {data_type_text.upper()} 字段'
    if operator_text not in _STRING_SAFE_OPERATORS:
        return False, (
            f'运算符 {operator_text} 不在 {data_type_text.upper()} '
            f'字段的安全算子集内')
    return True, ''


def _template_data_type(template: Any) -> Any:
    """安全取模板底层的 data_type（原子指标优先，派生指标次之，取不到返回 None）。

    派生模板的 atomic_metric 为 NULL，直接取属性会抛 RelatedObjectDoesNotExist，
    故显式判空；取不到时返回 None（分级函数对 None 按「非字符串类」处理 = 不限制，
    绝不因为取不到类型而误伤既有迁移路径）。
    """
    if template is None:
        return None
    am = getattr(template, 'atomic_metric', None)
    if am is not None and getattr(am, 'data_type', None):
        return am.data_type
    dm = getattr(template, 'derived_metric', None)
    if dm is not None and getattr(dm, 'data_type', None):
        return dm.data_type
    return None


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
    # 模板解析：兼容优先 find-or-create 指向 am 的启用模板
    # ------------------------------------------------------------------
    def _find_compatible_template(
        self, am: AtomicMetric, operator: Any,
    ) -> MetricTemplate | None:
        """在指向 am 的启用模板中找「operator 在其白名单内」的模板。

        MetricEngine 求值强制校验 operator ∈ template.operators（metric_engine.py:126-130 /
        :337-344），不在白名单即 error='模板不支持该运算符' + pass=False，最终表现为
        **候选人被静默拦截**。故复用必须以「运算符兼容」为第一判据，不能再无脑取第一个。

        Args:
            am: 目标 AtomicMetric。
            operator: 本条条件的运算符（ConditionItem.operator / JSON item 的 operator）。

        Returns:
            兼容的启用模板；无兼容模板返回 None（调用方需并入既有模板 / 新建 / SKIP）。
        """
        templates = MetricTemplate.objects.filter(
            atomic_metric=am, status=MetricStatus.ENABLED,
        )
        if not operator:
            # 空运算符（历史脏数据）不构成白名单约束：退化为旧行为，取任一启用模板。
            return templates.first()
        for template in templates:
            if operator in (template.operators or []):
                return template
        return None

    def _find_merge_candidate(self, am: AtomicMetric) -> MetricTemplate | None:
        """无兼容模板时，找出可「并入缺失算子」的既有启用模板（确定性：按 name 排序首个）。

        最小侵入原则：优先复用既有模板并只并入缺失的那 1 个 operator，
        **不新建重复命名模板、不开放无关算子**（尤其不开 UnifiedOperator 全集，
        理由见模块头「目标模板解析策略」）。
        """
        return MetricTemplate.objects.filter(
            atomic_metric=am, status=MetricStatus.ENABLED,
        ).first()

    def _merge_operator_into_template(
        self, template: MetricTemplate, operator: Any,
    ) -> MetricTemplate | None:
        """把 operator **追加**进既有模板的 operators（append-only，绝不删改既有项）。

        operators 只是「启用算子白名单」，追加只会放宽、不会破坏既有引用该模板的条件：
        既有条件允许的运算符全部保留，其 operator / value / 取值路径均不变。

        Returns:
            并入成功返回该模板；失败（operator 非法/写库异常/类型不兼容）返回 None。
        """
        if not operator or operator not in UnifiedOperator.values:
            return None
        # E-2 纵深防御：本方法是**唯一真正写 operators** 的入口，即便上层已做过分级校验，
        # 这里再拦一次 —— 绝不把数值/区间算子写进字符串类字段的共享白名单。
        allowed, reason = _operator_merge_policy(
            _template_data_type(template), operator)
        if not allowed:
            self.stderr.write(self.style.WARNING(
                f'  [SKIP] 并入被类型门禁拒绝 template={template.id}: {reason}'))
            return None
        current = list(template.operators or [])
        if operator in current:
            return template  # 已包含（理论不会走到，_find_compatible_template 已拦）
        try:
            # savepoint：写失败只回滚到本 savepoint，绝不污染外层事务
            with transaction.atomic():
                template.operators = current + [operator]
                template.save(update_fields=['operators', 'updated_at'])
        except IntegrityError as exc:
            self.stderr.write(self.style.WARNING(
                f'  [WARN] 并入算子失败 template={template.id} op={operator!r}: {exc}'))
            return None
        # 审计留痕（E-1，纯登记）：并入是对**全局共享实体**的永久性配置面变更
        # （operators 经 apps/process/views.py:958 透传给前端运算符下拉），且本命令
        # **不可回滚**；故必须留下「改了哪个模板、并入哪个算子、operators 从几个变到几个」。
        after_ops = current + [operator]
        self._record_relaxed_template(template, current, operator)
        self._apply_notes[str(template.id)] = (
            f'[并入 +{operator} 到既有模板 {template.id}'
            f'（operators {len(current)}→{len(after_ops)}：'
            f'{_format_ops(current)} → {_format_ops(after_ops)}）]')
        return template

    def _create_minimal_template(
        self, am: AtomicMetric, operator: Any,
    ) -> MetricTemplate | None:
        """新建**只含实际需要算子**的模板（operators = [operator]，绝不是全集）。

        name 唯一冲突时按候选名序列重试；每次 create 包在 transaction.atomic() 内，
        使 IntegrityError 只回滚到 savepoint —— 在嵌套事务（如 pytest 的 atomic 包裹）
        下也不会让整个事务进入 needs_rollback 而抛 TransactionManagementError。

        Returns:
            新建的模板；全部候选名冲突 / operator 非法 → None（调用方 SKIP + 报告）。
        """
        if not operator or operator not in UnifiedOperator.values:
            # 空运算符新建会得到「空白名单模板」= 不可求值 → 禁假绿，不建
            return None
        # E-2 纵深防御：新建同样过「类型 × 算子」分级。上层 _resolve_template 已放过，
        # 这里再拦一道，确保**没有任何写路径**能直接造出含数值/区间算子的字符串模板
        # （即便将来有人不经 _resolve_template 直接调本方法，也不破例）。
        allowed, reason = _operator_merge_policy(am.data_type, operator)
        if not allowed:
            self.stderr.write(self.style.WARNING(
                f'  [SKIP] 新建被类型门禁拒绝 atomic_metric={am.id}: {reason}'))
            return None
        # 只含本条实际需要的那 1 个算子（禁全集：字符串职级开 GT/BETWEEN 会产出恒 False 条件）
        operators = [operator]
        for candidate_name in self._candidate_template_names(am.name):
            try:
                with transaction.atomic():
                    created = MetricTemplate.objects.create(
                        name=candidate_name,
                        atomic_metric=am,
                        derived_metric=None,
                        operators=operators,
                        param_config={'min': None, 'max': None, 'step': None,
                                      'prefix': '', 'suffix': '', 'allOption': False},
                        value_domain={'segments': []},
                        param_enums=[],
                        param_allow_null=False,
                        status=MetricStatus.ENABLED,
                        description='auto-migrated from raw-path condition (LIFE-3)',
                    )
            except IntegrityError as exc:
                # name 唯一冲突（或同类约束冲突）→ 换下一个候选名重试；全部失败返回 None 由调用方 SKIP
                self.stderr.write(self.style.WARNING(
                    f'  [WARN] 新建模板名冲突 name={candidate_name!r}: {exc}，尝试下一个候选名'))
                continue
            # 审计留痕（E-1，纯登记）：新建模板同样会成为一个**新的全局共享实体**，
            # apply 输出必须能与「复用本就兼容的既有模板」在字面上区分开。
            self._apply_notes[str(created.id)] = (
                f'[新建模板 {created.id} operators={_format_ops(operators)}]')
            return created
        return None

    @staticmethod
    def _candidate_template_names(base_name: str) -> List[str]:
        """新建模板的候选名列表（按序尝试，规避 MetricTemplate.name 唯一冲突）。"""
        base_name = base_name or 'metric'
        return [
            _fit_template_name(base_name, ''),
            _fit_template_name(base_name, _NEW_TEMPLATE_SUFFIX),
            _fit_template_name(base_name, f'{_NEW_TEMPLATE_SUFFIX} {uuid.uuid4().hex[:6]}'),
        ]

    # ------------------------------------------------------------------
    # 可审计性登记（E-1，纯统计层：只登记、绝不参与任何迁移判定/写入）
    # ------------------------------------------------------------------
    def _reset_audit_state(self) -> None:
        """初始化本轮的可审计计数器（每次 handle 开头调用）。

        - _relaxed_templates: 被（或将被）放宽白名单的既有共享模板，
          key=模板 id，value={'label': 模板名, 'before': 原 operators, 'added': 并入的算子}。
        - _apply_notes: 本条 --apply 输出的模板后缀（一次性消费），
          key=模板 id；未登记即表示「复用了本就兼容的模板」。
        - _gate_reason: 本条最近一次「类型 × 算子」门禁拒绝原因（'' 表示未被拒），
          由 _resolve_template / _plan_template_note 写入，供调用方分桶报告。
        """
        self._relaxed_templates: Dict[str, Dict[str, Any]] = {}
        self._apply_notes: Dict[str, str] = {}
        self._gate_reason: str = ''

    def _record_operator_skip(self, path: Any, operator: Any, gate_reason: str = '') -> None:
        """登记一条「因运算符不可写入白名单而被 SKIP」的项（按原因分桶）。

        两桶分开是为了事后可审计「到底是无法兼容，还是被类型门禁主动拦下」：
          - gate_reason 非空 → _skipped_type_operator（E-2 类型 × 算子不兼容，主动拒绝）；
          - 否则           → _skipped_operator（既有的「无兼容模板且无法新建」桶）。
        """
        op_key = f'{path} [{operator}]'
        if gate_reason:

            self._skipped_type_operator[op_key] = (
                self._skipped_type_operator.get(op_key, 0) + 1)
        else:
            self._skipped_operator[op_key] = self._skipped_operator.get(op_key, 0) + 1

    @staticmethod
    def _skip_reason_text(operator: Any, gate_reason: str = '') -> str:
        """SKIP 文案里的「原因短语」：类型门禁优先，否则回落为既有的「无兼容模板」措辞。

        抽成方法是为了避免嵌套同引号 f-string（PEP 701 之前不合法），并让
        dry-run / --apply 两个分支共用同一措辞（口径一致）。
        """
        if gate_reason:
            return gate_reason
        return f'运算符 {operator} 无兼容模板'

    def _record_relaxed_template(
        self, template: MetricTemplate, before_ops: List[Any], operator: Any,
    ) -> None:
        """登记一个「被放宽白名单」的既有模板（同一模板被并入多个算子时合并显示）。

        --apply 由 _merge_operator_into_template 在**写库成功后**登记（实际发生）；
        dry-run 由 _plan_template_note 在预测为「并入」时登记（计划发生）。
        两者写入同一结构，故 dry-run 报告与 --apply 报告给出同一份清单，口径不矛盾。
        """
        key = str(template.id)
        record = self._relaxed_templates.get(key)
        if record is None:
            record = {
                'label': (template.name or '').strip(),
                'before': list(before_ops or []),
                'added': [],
            }
            self._relaxed_templates[key] = record
        if operator and operator not in record['before'] and operator not in record['added']:
            record['added'].append(operator)

    def _take_apply_template_note(self, template: MetricTemplate) -> str:
        """取本条 --apply 输出的模板后缀（**一次性消费**）：区分复用 / 并入 / 新建。

        _merge_operator_into_template / _create_minimal_template 在写库成功时登记后缀；
        未被登记 ⇒ 复用了本就兼容的既有模板 ⇒ 保持 `[模板 X]`。
        一次性消费保证「同一模板被后续条目复用」时不会再重复打印并入/新建文案。
        """
        return self._apply_notes.pop(str(template.id), f'[模板 {template.id}]')

    def _resolve_template(
        self, am: AtomicMetric, operator: Any, allow_create: bool = True,
    ) -> MetricTemplate | None:
        """解析本条条件的目标模板：**兼容优先 → 最小侵入并入 → 最小算子新建**。

        硬约束：绝不返回「operator 不在 operators 内」的模板（那会产出恒 False 的坏条件）；
        绝不新建「全集 operators」模板（会在字符串职级上产出「职级 > 5」这类恒 False 配置）。

        策略（按序）：
          1. 复用指向 am 的启用模板中 **operator 已在其 operators 内** 的那个（兼容优先）。
          2. 无兼容模板 → 复用指向 am 的既有启用模板，**只把缺失的那 1 个 operator 追加**
             进其 operators（append-only，放宽白名单，不破坏既有引用条件）。
          3. 无既有模板 / 并入失败 → 新建模板，operators **只含本条实际需要的算子**
             （name 走候选名序列重试，规避 unique 冲突）。
          4. operator 不是合法 UnifiedOperator 取值 → 返回 None（SKIP）。
          5. 以上都失败 → 返回 None（SKIP）。

        ⚠️ E-2 门禁：步骤 2（并入）与步骤 3（新建）都会把 operator **写进**共享白名单，
        故二者之前统一过一道「类型 × 算子」分级（_operator_merge_policy）：
        字符串类字段遇数值比较/区间算子 → 直接返回 None（SKIP + 报告），
        绝不并入、绝不新建（否则「职级 > 5」会变成可配却恒 False 的假及格配置）。

        Args:
            am: 目标 AtomicMetric。
            operator: 本条条件的运算符。
            allow_create: False 表示只读解析（dry-run 用它做预测，保证零写入）。

        Returns:
            目标模板；None 表示无法产出可求值条件，调用方**必须 SKIP + 报告**。
            SKIP 原因（若因类型门禁被拒）写入 self._gate_reason，供调用方分桶报告。
        """
        self._gate_reason = ''
        compatible = self._find_compatible_template(am, operator)
        if compatible is not None:
            return compatible
        # 全集已废弃：operator 本身不是合法 UnifiedOperator → 谁也覆盖不了 → SKIP
        if operator and operator not in UnifiedOperator.values:
            return None
        merge_candidate = self._find_merge_candidate(am)
        if allow_create:
            # --- --apply：可写 ---
            # E-2：并入 / 新建都会写共享白名单 → 写之前先过「类型 × 算子」分级门禁
            allowed, reason = _operator_merge_policy(am.data_type, operator)
            if not allowed:
                self._gate_reason = reason
                return None
            if merge_candidate is not None and operator:
                merged = self._merge_operator_into_template(merge_candidate, operator)
                if merged is not None:
                    return merged
            # 无既有模板可并入（或并入失败 / 运算符为空）→ 新建最小算子模板
            return self._create_minimal_template(am, operator)
        # --- dry-run：只读预测，绝不写库（返回 None，由 _plan_template_note 出预测文案）---
        return None

    def _plan_template_note(
        self, am: AtomicMetric, operator: Any,
    ) -> Tuple[str, bool]:
        """dry-run 预测：本条将「复用兼容模板 / 并入既有模板 / 新建最小算子模板 / SKIP」。

        仅查询、绝不写库（只读复用 / 并入 / 新建三选一的预测，内部绝不触发写操作）。

        与 --apply 共用同一套判定（含 E-2「类型 × 算子」分级），故 dry-run 与 --apply
        口径**严格一致**：被门禁拒绝时预测文案同步为
        `[SKIP 运算符 GT 不适用于 STRING 字段 demand.level]`。

        Returns:
            (note, ok)：ok=False 表示预测为不可求值（调用方应按 SKIP 计数，不计入 migrated）。
            因类型门禁被拒时，原因写入 self._gate_reason，供调用方分桶报告。
        """
        self._gate_reason = ''
        compatible = self._find_compatible_template(am, operator)
        if compatible is not None:
            return f' [复用兼容模板 {compatible.id}]', True
        if operator and operator not in UnifiedOperator.values:
            return f' [SKIP 运算符 {operator} 非合法 UnifiedOperator]', False
        # E-2：与 --apply 同口径 —— 写入共享白名单前先过「类型 × 算子」分级门禁
        allowed, reason = _operator_merge_policy(am.data_type, operator)
        if not allowed:
            self._gate_reason = reason
            field_path = getattr(am, 'source_path', '') or ''
            return f' [SKIP {reason} {field_path}]', False
        merge_candidate = self._find_merge_candidate(am)
        if merge_candidate is not None and operator:
            # 计划放宽也要登记（零写入，仅内存计数）：使 dry-run 报告与 --apply 报告
            # 给出**同一份**「哪些共享模板会被放宽」的清单，口径不矛盾。
            self._record_relaxed_template(
                merge_candidate, list(merge_candidate.operators or []), operator)
            return (
                f' [将复用既有模板 {merge_candidate.id} 并仅并入 {operator}]', True)
        if not operator:
            # 空运算符：无兼容/既有模板可并入，新建只会得到空白名单模板（不可求值）→ SKIP
            return ' [SKIP 运算符为空且无可复用模板]', False
        return f' [将新建模板 operators=[{operator}]]', True

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
        - 无兼容模板可复用且新建失败的项计入 self._skipped_operator，不迁移、不改写。
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
                operator = item.get('operator')
                # 仅处理裸路径（在 source_types 内且 field 非模板 id）的项
                if ctype in source_types and not _looks_like_id(field):
                    path = field
                    try:
                        # 精确匹配优先，legacy 大写常量规范化仅作兜底（统一入口，避免两处逻辑漂移）
                        am, resolved = _resolve_atomic_metric(path)
                    except Exception as exc:  # noqa: BLE001 — 单条查询异常不中断整批
                        err_count += 1
                        self.stderr.write(self.style.ERROR(
                            f'  [ERROR] StageRule {sr_id} {bucket} 查 AtomicMetric 异常 '
                            f'path={path!r}: {exc}'))
                        new_items.append(item)
                        continue
                    if am is None:
                        self._skipped_no_atomic[path] = self._skipped_no_atomic.get(path, 0) + 1
                        if resolved != path:
                            # 报告溯源：本条已尝试规范化为 resolved，仍无匹配
                            self._skipped_normalized[path] = resolved
                        new_items.append(item)
                        continue
                    norm_note = '' if resolved == path else f' [经规范化匹配 {path} -> {resolved}]'
                    if resolved != path:
                        # 兜底映射命中（dry-run / apply 都记，保证 --apply 后仍可审计）
                        hit_key = f'{path} -> {resolved}'
                        self._normalized_hits[hit_key] = self._normalized_hits.get(hit_key, 0) + 1
                    if dry_run:
                        # dry-run 不写库：仅预测「复用兼容模板 / 并入既有模板 / 新建最小算子模板 / SKIP」
                        plan_note, ok = self._plan_template_note(am, operator)
                        if not ok:
                            # 预测不可求值（含 E-2 类型门禁拒绝）→ 不改、不计 migrated；
                            # 同步打印 SKIP 计划文案，与 --apply 口径一致
                            self._record_operator_skip(path, operator, self._gate_reason)
                            self.stdout.write(self.style.WARNING(
                                f'{prefix}[SKIP] StageRule {sr_id} {bucket} item: '
                                f'{self._skip_reason_text(operator, self._gate_reason)}'
                                f'（path={path}）：不迁移、不改写、不建不兼容模板'
                                f'{plan_note}'))
                            new_items.append(item)
                            continue
                        migrated += 1
                        self.stdout.write(
                            f'{prefix}将改写 StageRule {sr_id} {bucket} item: '
                            f'{ctype} {path} -> METRIC{plan_note}{norm_note}')
                        new_items.append(item)  # dry-run 不改写原 item
                    else:
                        try:
                            template = self._resolve_template(am, operator)
                        except IntegrityError as exc:
                            # 模板 name 唯一约束等冲突：降级跳过该条，不崩（绝不产出不兼容模板）
                            err_count += 1
                            self.stderr.write(self.style.ERROR(
                                f'  [ERROR] StageRule {sr_id} {bucket} 建模板冲突 path={path!r}: {exc}'))
                            new_items.append(item)
                            continue
                        if template is None:
                            # 无兼容可复用 + 新建失败 / operator 非法 / 类型门禁拒绝 → SKIP
                            gate_reason = self._gate_reason
                            self._record_operator_skip(path, operator, gate_reason)
                            self.stderr.write(self.style.WARNING(
                                f'  [SKIP] StageRule {sr_id} {bucket} '
                                f'{self._skip_reason_text(operator, gate_reason)}'
                                f'（path={path}）：不迁移、不改写、不建不兼容模板'))
                            new_items.append(item)
                            continue
                        migrated += 1
                        # E-1：模板后缀区分「复用兼容 / 并入放宽 / 新建」，便于事后审计
                        tmpl_note = self._take_apply_template_note(template)
                        self.stdout.write(
                            f'{prefix}已改写 StageRule {sr_id} {bucket} item: '
                            f'{ctype} {path} -> METRIC {tmpl_note}{norm_note}')
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
        # SKIP 溯源：原 field -> 已尝试规范化后的候选 path（仍无匹配时记录，便于排查）
        self._skipped_normalized: Dict[str, str] = {}
        # SKIP(运算符不兼容)：无兼容模板可复用，且无法并入既有模板 / 无法新建兼容模板
        # → 记录 ('path [OP]', 条数)
        self._skipped_operator: Dict[str, int] = {}
        # SKIP(E-2 类型 × 算子不兼容)：目标字段是字符串类而 operator 是数值比较/区间算子
        # → 不并入、不新建、不改写（禁假绿），记录 ('path [OP]', 条数)
        self._skipped_type_operator: Dict[str, int] = {}
        # 兜底映射命中审计：legacy 大写常量经规范化命中 enabled AtomicMetric 的条数（按 X -> y 归档）
        self._normalized_hits: Dict[str, int] = {}
        self._reset_audit_state()
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
                # 精确匹配优先，legacy 大写常量规范化仅作兜底（统一入口，避免两处逻辑漂移）
                am, resolved = _resolve_atomic_metric(path)
                if am is None:
                    self._skipped_no_atomic[path] = self._skipped_no_atomic.get(path, 0) + 1
                    if resolved != path:
                        # 报告溯源：本条已尝试规范化为 resolved，仍无匹配
                        self._skipped_normalized[path] = resolved
                    continue
                norm_note = '' if resolved == path else f' [经规范化匹配 {path} -> {resolved}]'
                if resolved != path:
                    # 兜底映射命中（dry-run / apply 都记，保证 --apply 后仍可审计）
                    key = f'{path} -> {resolved}'
                    self._normalized_hits[key] = self._normalized_hits.get(key, 0) + 1
                ctype_orig = ci.condition_type  # 改写前留存，供 apply 分支打印原始类型
                if dry_run:
                    # dry-run 不写库：仅预测「复用兼容模板 / 并入既有模板 / 新建最小算子模板 / SKIP」
                    plan_note, ok = self._plan_template_note(am, ci.operator)
                    if not ok:
                        # 预测即不可求值（含 E-2 类型门禁拒绝）→ 按 SKIP 处理，
                        # 绝不计入 migrated（禁假绿）。
                        # 同步打印 SKIP 计划文案（含 E-2 的「不适用于 STRING 字段 X」），
                        # 保证 dry-run 与 --apply 口径一致、事后可审计。
                        self._record_operator_skip(path, ci.operator, self._gate_reason)
                        self.stdout.write(self.style.WARNING(
                            f'{prefix}[SKIP] ConditionItem {ci.id}: '
                            f'{self._skip_reason_text(ci.operator, self._gate_reason)}'
                            f'（path={path}）：不迁移、不改写、不建不兼容模板{plan_note}'))
                        continue
                    self.stdout.write(
                        f'{prefix}将改写 ConditionItem {ci.id}: '
                        f'{ci.condition_type} {path} -> METRIC{plan_note}{norm_note}')
                else:
                    template = self._resolve_template(am, ci.operator)
                    if template is None:
                        # 无兼容可复用 + 新建失败 / operator 非法 / 类型门禁拒绝 → SKIP
                        # （绝不产出不可求值条件）
                        gate_reason = self._gate_reason
                        self._record_operator_skip(path, ci.operator, gate_reason)
                        self.stderr.write(self.style.WARNING(
                            f'  [SKIP] ConditionItem {ci.id} '
                            f'{self._skip_reason_text(ci.operator, gate_reason)}'
                            f'（path={path}）：不迁移、不改写、不建不兼容模板'))
                        continue
                    ci.condition_type = ConditionFieldType.METRIC
                    ci.field = str(template.id)
                    ci.save(update_fields=['condition_type', 'field', 'updated_at'])
                    # E-1：模板后缀区分「复用兼容 / 并入放宽 / 新建」，便于事后审计；
                    # --apply 也打印兜底映射提示（事后可审计）
                    tmpl_note = self._take_apply_template_note(template)
                    self.stdout.write(
                        f'{prefix}已改写 ConditionItem {ci.id}: '
                        f'{ctype_orig} {path} -> METRIC '
                        f'{tmpl_note}{norm_note}')
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
        if self._skipped_normalized:
            nparts = ', '.join(
                f'{k} -> {v}' for k, v in sorted(self._skipped_normalized.items()))
            self.stdout.write(
                f'{prefix}SKIP 已尝试 legacy 规范化（仍无匹配）：{nparts}')
        if self._skipped_operator:
            oparts = ', '.join(
                f'{k}: {v}' for k, v in sorted(self._skipped_operator.items()))
            self.stdout.write(self.style.WARNING(
                f'{prefix}SKIP(运算符不在任何可复用模板白名单且无法新建兼容模板)：{oparts}'))
        if self._skipped_type_operator:
            tparts = ', '.join(
                f'{k}: {v}' for k, v in sorted(self._skipped_type_operator.items()))
            self.stdout.write(self.style.WARNING(
                f'{prefix}SKIP(运算符不适用于该字段数据类型，已拒绝并入/新建)：{tparts}'))
        if self._normalized_hits:
            total_hits = sum(self._normalized_hits.values())
            hparts = ', '.join(
                f'{k}: {v}' for k, v in sorted(self._normalized_hits.items()))
            self.stdout.write(self.style.WARNING(
                f'{prefix}已用兜底映射命中：{total_hits} 条（{hparts}）—— '
                f'legacy 形态属尽力映射，需人工核对语义与配置值'))
        # 已放宽（/将放宽）既有模板白名单 —— 对**全局共享实体**的永久配置面变更
        # （operators 经 apps/process/views.py:958 透传给前端运算符下拉）且本命令不可回滚，
        # 必须留下「哪些模板被放宽、operators 从几个变到几个」的完整清单。
        verb = '将放宽' if dry_run else '已放宽'
        if self._relaxed_templates:
            self.stdout.write(self.style.WARNING(
                f'{prefix}{verb}既有模板白名单（共享实体，不可回滚）：'
                f'{len(self._relaxed_templates)} 个'))
            for tid in sorted(self._relaxed_templates):
                record = self._relaxed_templates[tid]
                display = f'{record["label"]} ({tid})' if record['label'] else tid
                self.stdout.write(self.style.WARNING(
                    f'{prefix}  - {display}: {_format_ops(record["before"])} → '
                    f'{_format_ops(record["before"] + record["added"])}'))
        else:
            # 0 个也要显式打印：否则事后无法证明「没有共享模板被放宽」
            self.stdout.write(f'{prefix}{verb}既有模板白名单：0 个')
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
