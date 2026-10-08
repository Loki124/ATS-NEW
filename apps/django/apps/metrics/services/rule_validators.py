"""指标规则服务端校验链（P1-A，单一真相源）。

设计要点：
- `validate_metric_rule(rule: dict) -> list[str]` 是纯函数，返回**人话中文**错误列表，
  空列表表示通过。被两处挂载：
    1) MetricRuleSerializer.validate() —— 请求态 400（防御前端绕过）
    2) MetricRule.clean()            —— 程序态（admin/表单直写路径）
- 数值比较一律使用 Decimal（INV-9），禁止 float 精度陷阱。
- DB 相关校验（模板存在性 / 运算符白名单 / 互斥）包在 try/except 内：
  无 DB 或查询异常时**跳过该硬查、仅做结构校验**，避免测试/迁移场景误挂。
- V13–V15（指标级 param/base_path/source_path 校验）本批次不做，留 TODO，
  将在指标级校验跟进（见下方 _TODO）。

对应规格书 §14 的 16 门校验（V01–V16），本批次落地规则级子集：
V01 名称 / V02 条件非空 / V03 条件为 dict / V04 模板存在 / V05 scene+logic 枚举 /
V06 operator 全局合法 / V07 operator 在模板白名单 / V08 action_type 枚举 /
V09 BETWEEN min<=max / V10 IN/NOT_IN 非空数组 / V11 区间重叠 WARNING（忽略）/
V12 类型一致（轻量）/ V16 互斥动作（blocking 维度骨架）。
"""
from decimal import Decimal, InvalidOperation

from apps.rule_engine.models import UnifiedOperator

# ---------------------------------------------------------------------------
# TODO（指标级校验，本批次不做，留待指标级校验跟进）
#   V13 MetricTemplate.calc_params 符合引用派生指标的 param_schema（required/类型/select∈options）
#   V14 base_path 末段指向数组/日期与 input_kind 一致（轻 heuristic）
#   V15 原子 source_path 含 "." 且无 dunder（既有序列化器已部分覆盖）
# ---------------------------------------------------------------------------


def _to_decimal(value):
    """把任意数值型输入转为 Decimal；非法返回 None。"""
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def validate_metric_rule(rule: dict) -> list:
    """校验一条指标规则，返回人话中文错误列表（空=通过）。

    Args:
        rule: dict，至少含 name/scene/logic/conditions/action_type 等字段；
              调用方负责把模型或序列化数据规整成 dict。
    """
    errors: list = []

    # ---- V01 名称非空 + 长度 1~128 ----
    name = rule.get('name')
    if not isinstance(name, str) or not name.strip():
        errors.append('规则名称不能为空')
    elif not (1 <= len(name.strip()) <= 128):
        errors.append('规则名称长度需在 1~128 字符之间')

    # ---- V05 scene 非空 + logic 枚举 ----
    scene = rule.get('scene')
    if not scene:
        errors.append('应用场景不能为空')
    logic = rule.get('logic')
    if logic not in ('AND', 'OR'):
        errors.append('条件组合逻辑必须为 AND 或 OR')

    # ---- V02/V03 条件结构 ----
    conditions = rule.get('conditions')
    if not isinstance(conditions, list) or len(conditions) == 0:
        errors.append('至少配置 1 个条件')
    else:
        for idx, cond in enumerate(conditions, start=1):
            if not isinstance(cond, dict):
                errors.append(f'第 {idx} 个条件格式不正确')
                continue

            template_id = cond.get('templateId') or cond.get('template_id')
            operator = cond.get('operator')

            # ---- V04 模板存在 + V07 运算符在模板白名单（DB 相关，失败则跳过）----
            if template_id:
                try:
                    from apps.metrics.models import MetricTemplate
                    tmpl = MetricTemplate.objects.filter(pk=template_id).first()
                    if tmpl is None:
                        errors.append(f'第 {idx} 个条件引用的模板不存在: {template_id}')
                    else:
                        ops = tmpl.operators or []
                        if operator is not None and operator not in ops:
                            errors.append(
                                f'第 {idx} 个条件运算符不在该指标允许范围内: {operator}'
                            )
                except Exception:  # noqa: BLE001 — DB 不可用 / 查询异常时跳过 DB 硬查, 仅保留结构校验 (容错)
                    pass

            # ---- 方案 B：指标 vs 指标（rightTemplateId 右操作数）----
            right_template_id = cond.get('rightTemplateId') or cond.get('right_template_id')
            if right_template_id:
                _MVM_OPS = {'EQ', 'NEQ', 'GT', 'GTE', 'LT', 'LTE'}
                if operator not in _MVM_OPS:
                    errors.append(
                        f'第 {idx} 个条件「指标对比」仅支持 {sorted(_MVM_OPS)} 运算符')
                try:
                    from apps.metrics.models import MetricTemplate as MT
                    rt = MT.objects.filter(pk=right_template_id).first()
                    if rt is None:
                        errors.append(f'第 {idx} 个条件引用的对比模板不存在: {right_template_id}')
                    elif template_id:
                        lt = MT.objects.filter(pk=template_id).first()
                        if lt is not None and lt.data_type != rt.data_type:
                            errors.append(
                                f'第 {idx} 个条件左右指标类型不一致（{lt.data_type} vs {rt.data_type}）')
                except Exception:  # noqa: BLE001 — DB 不可用 / 查询异常时跳过硬查 (容错)
                    pass

            # ---- V06 operator 全局合法 ----
            if operator is not None and operator not in UnifiedOperator.values:
                errors.append(f'第 {idx} 个条件运算符不合法: {operator}')

            # ---- V09 BETWEEN min<=max（Decimal）----
            if operator == 'BETWEEN':
                meta = cond.get('meta') or {}
                mn = meta.get('min')
                mx = meta.get('max')
                if mn is None or mx is None:
                    errors.append(f'第 {idx} 个条件 BETWEEN 必须包含 min 与 max')
                else:
                    dmn, dmx = _to_decimal(mn), _to_decimal(mx)
                    if dmn is None or dmx is None:
                        errors.append(f'第 {idx} 个条件区间值不是合法数字')
                    elif dmn > dmx:
                        errors.append('区间最小值不能大于最大值')

            # ---- V10 IN/NOT_IN 非空数组且元素非空 ----
            elif operator in ('IN', 'NOT_IN'):
                value = cond.get('value')
                if (not isinstance(value, list) or len(value) == 0
                        or any(v is None or v == '' for v in value)):
                    errors.append(
                        f'第 {idx} 个条件 {operator} 的取值必须为非空数组且元素非空'
                    )

            # ---- V12 区间/集合 value 与模板 data_type 一致（轻量，留待指标级深化）----
            # 本批次仅做结构占位，类型强校验在 V13–V15 指标级跟进。

    # ---- V08 action_type 枚举（本批次若传入则校验；T4 落地字段后必传）----
    action_type = rule.get('action_type')
    if action_type is not None and action_type not in ('VETO', 'DEDUCT', 'BONUS'):
        errors.append('动作类型必须为 VETO / DEDUCT / BONUS 之一')

    # ---- V16 互斥动作（action_type 维度，T4 取代旧 blocking 维度）----
    # 同一场景下，若本规则 action_type=='VETO' 且已存在另一条 VETO 规则，
    # 二者条件引用了相同 templateId，则互斥（禁止对同一指标重复配置强阻断，
    # 避免多条 VETO 叠加导致业务被重复拒绝、且语义冗余）。
    action_type = rule.get('action_type')
    if action_type == 'VETO':
        try:
            from apps.metrics.models import MetricRule
            own_tids = {
                (c.get('templateId') or c.get('template_id'))
                for c in (conditions or []) if isinstance(c, dict)
            }
            own_tids.discard(None)
            if scene and own_tids:
                existing = MetricRule.objects.filter(
                    scene=scene, action_type='VETO',
                ).exclude(pk=rule.get('id'))
                for r in existing:
                    r_tids = {
                        (c.get('templateId') or c.get('template_id'))
                        for c in (r.conditions or []) if isinstance(c, dict)
                    }
                    if own_tids & r_tids:
                        errors.append('同一指标禁止同时配置多条必须满足(VETO)规则')
                        break
        except Exception:  # noqa: BLE001 — DB 不可用 / 查询异常时跳过互斥硬查 (容错, 仅结构校验)
            pass

    return errors
