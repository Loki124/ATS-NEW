"""候选人数据快照 —— 把 ORM 组装成规则引擎可解析的嵌套 dict。

这是「无需频繁开发的指标库」能否真正落地的**最后一块拼图**：
    原子指标只写 source_path（如 candidate.age），取值由本模块把真实业务对象
    组装成嵌套 dict 供 FieldResolver 解析。运营新增指标时不需要开发介入 ——
    前提是该字段已进入快照。

数据来源（三层，逐层叠加，后者不覆盖前者已占的键）：
    1. Candidate 主表白名单字段（snake_case 原样）
    2. Candidate.extra JSONField 展开（业务若把结构化经历塞这里，派生指标即可用）
    3. 扩展字段值：apps.candidate.CandidateFieldValue + dynamic_field.DynamicFieldValue

⚠️ 已知数据现状（2026-09-25 勘察）：项目**没有**独立的「工作经历 / 教育经历」
结构化模型（全仓仅 metrics 自身示例命中）。因此：
    - candidate.age / highest_education / work_years 等主表字段 ✅ 真实可用
    - 空窗期 / 跳槽频率 / 最高学历(按经历列表算) 这类派生指标，需要经历数据
      先落进 candidate.extra 或建独立模型，才能对真实数据生效（见文档待办）。

安全：敏感字段（手机号/邮箱/证件/薪资）默认**不进快照**，也不出现在可引用字段
清单里 —— 避免运营无意中把敏感数据写进规则条件与执行结果（对齐 field_acl 脱敏约定）。
"""
from __future__ import annotations

from typing import Any, Dict, List

# 快照根键（与示例数据结构一致，保证规则条件两边通用）
ROOT_KEY = 'candidate'

# 主表可进快照的白名单字段（snake_case）→ (展示名, 指标数据类型)
BASIC_FIELDS: List[tuple] = [
    ('id', '候选人ID', 'string'),
    ('name', '姓名', 'string'),
    ('gender', '性别', 'string'),
    ('age', '年龄', 'number'),
    ('birth_date', '出生日期', 'date'),
    ('highest_education', '最高学历', 'string'),
    ('work_years', '工作年限', 'number'),
    ('current_city', '当前城市', 'string'),
    ('expected_city', '期望城市', 'string'),
    ('current_company', '当前公司', 'string'),
    ('current_position', '当前职位', 'string'),
    ('school_tag', '学校标签', 'string'),
    ('major_tag', '专业标签', 'string'),
    ('resume_score', '简历评分', 'number'),
]

# 敏感字段：默认排除（不进快照、不进可引用清单）
SENSITIVE_FIELDS = {'phone', 'phone_hash', 'email', 'email_hash',
                    'id_card_hash', 'id_card_no', 'expected_salary', 'salary'}


def build_candidate_snapshot(candidate_id: str, *, include_sensitive: bool = False) -> Dict[str, Any]:
    """组装单个候选人的规则快照 `{'candidate': {...}}`。

    候选人不存在时返回 `{'candidate': {}}`（不抛异常，交由引擎判"字段解析失败"）。
    """
    from apps.candidate.models import Candidate, CandidateFieldValue

    candidate = Candidate.objects.filter(pk=candidate_id).first()
    if candidate is None:
        return {ROOT_KEY: {}}

    node: Dict[str, Any] = {}

    # 1) 主表白名单字段
    for field, _label, _dtype in BASIC_FIELDS:
        node[field] = _jsonable(getattr(candidate, field, None))

    if include_sensitive:
        for field in SENSITIVE_FIELDS:
            if hasattr(candidate, field):
                node[field] = _jsonable(getattr(candidate, field, None))

    # 2) extra JSONField 展开（业务结构化数据入口，如 workExperience / education）
    extra = getattr(candidate, 'extra', None)
    if isinstance(extra, dict):
        for key, value in extra.items():
            if key in SENSITIVE_FIELDS and not include_sensitive:
                continue
            node.setdefault(key, value)

    # 3) 扩展字段值（标准简历扩展列 + 动态字段），主表已占的键不被覆盖
    for field_key, value in CandidateFieldValue.objects.filter(
        candidate_id=candidate_id
    ).values_list('field_key', 'value'):
        node.setdefault(field_key, value)

    try:
        from apps.dynamic_field.models import DynamicFieldValue
        for field_key, value in DynamicFieldValue.objects.filter(
            resource='Candidate', entity_id=str(candidate_id)
        ).values_list('field_key', 'value'):
            node.setdefault(field_key, value)
    except Exception:
        # dynamic_field 不可用时不影响主快照（降级，绝不 500）
        pass

    return {ROOT_KEY: node}


def list_candidate_paths() -> List[Dict[str, str]]:
    """可引用的字段路径清单 —— 供配置原子指标时下拉选择，避免手填路径出错。

    组成：主表白名单字段（固定）+ 已定义的动态字段（resource=Candidate，动态）。
    """
    paths: List[Dict[str, str]] = []
    for field, label, dtype in BASIC_FIELDS:
        paths.append({
            'path': f'{ROOT_KEY}.{field}',
            'label': label,
            'dataType': dtype,
            'source': 'model',
        })

    try:
        from apps.dynamic_field.models import DynamicField
        rows = DynamicField.objects.filter(resource='Candidate').values_list(
            'field_key', 'label', 'field_type'
        )
        for field_key, label, field_type in rows:
            paths.append({
                'path': f'{ROOT_KEY}.{field_key}',
                'label': label or field_key,
                'dataType': _dynamic_type_to_metric(field_type),
                'source': 'dynamic',
            })
    except Exception:
        pass

    return paths


def _dynamic_type_to_metric(field_type: str) -> str:
    """动态字段类型 → 指标数据类型（粗粒度映射，够用即可）。"""
    if not field_type:
        return 'string'
    ft = str(field_type).upper()
    if 'NUMBER' in ft or 'INT' in ft:
        return 'number'
    if 'DATE' in ft or 'TIME' in ft:
        return 'date'
    if 'BOOL' in ft or 'SWITCH' in ft:
        return 'boolean'
    return 'string'


def _jsonable(value: Any) -> Any:
    """把 ORM 值转为可 JSON 序列化（date/Decimal → str）。"""
    if value is None:
        return None
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    if isinstance(value, (int, bool)):
        return value
    try:
        from decimal import Decimal
        if isinstance(value, Decimal):
            return float(value)
    except Exception:
        pass
    return value
