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

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# 快照根键（与示例数据结构一致，保证规则条件两边通用）
ROOT_KEY = 'candidate'

# 主表可进快照的白名单字段（snake_case）→ (展示名, 指标数据类型)
# 覆盖 AtomicMetric 0009/0010 迁移 seed 的全部 24 个候选对象路径指标，使目录列出的指标
# 都能真实求值（避免「指标可定义却永远算不出」的假绿）。字段名与 Candidate 主表标量字段
# 一一对应；任意字段不存在时 getattr(..., None) 安全降级为 None（不报错）。
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
    # —— 以下为 0010 迁移 seed 的候选主表字段，纳入快照使其可真实求值 ——
    ('recruit_type', '招聘类型', 'string'),
    ('resume_file_url', '简历文件地址', 'string'),
    ('resume_text', '简历文本', 'string'),
    ('referral_type', '内推类型', 'string'),
    ('current_state', '候选人当前状态', 'string'),
    ('is_blacklisted', '是否黑名单', 'boolean'),
    ('blacklist_reason', '黑名单原因', 'string'),
    ('moka_candidate_id', 'Moka候选人ID', 'string'),
    ('is_archived', '是否归档', 'boolean'),
    ('archived_at', '归档时间', 'date'),
]

# 敏感字段：默认排除（不进快照、不进可引用清单）
SENSITIVE_FIELDS = {'phone', 'phone_hash', 'email', 'email_hash',
                    'id_card_hash', 'id_card_no', 'expected_salary', 'salary'}


def build_candidate_snapshot(candidate_id: str, *, include_sensitive: bool = False) -> Dict[str, Any]:
    """组装单个候选人的规则快照 `{'candidate': {...}}`。

    候选人不存在时返回 `{'candidate': {}}`（不抛异常，交由引擎判"字段解析失败"）。

    内部委托 build_candidate_snapshots 批量接口，单候选调用亦走 IN 预取
    (per P1 audit 候选快照 N+1 修复: 评分一批 N 候选从 O(N) 查询降为 O(1))。
    """
    snapshots = build_candidate_snapshots([candidate_id], include_sensitive=include_sensitive)
    return snapshots.get(str(candidate_id), {ROOT_KEY: {}})


def build_candidate_snapshots(
    candidate_ids: List[str], *, include_sensitive: bool = False
) -> Dict[str, Dict[str, Any]]:
    """批量组装多候选人的规则快照 —— 一次 IN 查询取整批字段值，避免逐候选 N+1 (per P1 audit)。

    返回 {candidate_id: {'candidate': node}}，单候选结构与 build_candidate_snapshot 完全一致，
    保证指标引擎消费的快照结构不变。评分一批 N 候选时调用本函数，可把快照查询从 O(N) 降为 O(1)。
    """
    from apps.candidate.models import Candidate, CandidateFieldValue
    from apps.dynamic_field.models import DynamicFieldValue

    ids = [str(c) for c in (candidate_ids or [])]
    result: Dict[str, Dict[str, Any]] = {}

    # 1) 候选主表一次 IN 查询，逐候选拼装白名单/age 回填/extra 节点（纯内存，零额外查询）
    candidates = {
        str(c.pk): c
        for c in Candidate.objects.filter(pk__in=ids)
    }
    for cid, candidate in candidates.items():
        result[cid] = {ROOT_KEY: _build_basic_node(candidate, include_sensitive=include_sensitive)}

    if not result:
        return result

    # 2) 扩展字段值（标准简历扩展列）—— 单条 IN 查询取整批
    for candidate_id, field_key, value in CandidateFieldValue.objects.filter(
        candidate_id__in=ids,
    ).values_list('candidate_id', 'field_key', 'value'):
        node = result.get(str(candidate_id), {}).get(ROOT_KEY)
        if node is not None:
            node.setdefault(field_key, value)

    # 3) 动态字段值 —— 单条 IN 查询取整批 (dynamic_field 不可用时降级, 不阻断主快照)
    try:
        for candidate_id, field_key, value in DynamicFieldValue.objects.filter(
            resource='Candidate', entity_id__in=ids,
        ).values_list('field_key', 'value', 'entity_id'):
            node = result.get(str(candidate_id), {}).get(ROOT_KEY)
            if node is not None:
                node.setdefault(field_key, value)
    except Exception as e:  # noqa: BLE001 — dynamic_field 不可用时不阻断主快照 (降级, 绝不 500)
        logger.warning('candidate_snapshot 批量 dynamic_field 查询失败: %s', e, exc_info=True)

    return result


def _build_basic_node(candidate, *, include_sensitive: bool = False) -> Dict[str, Any]:
    """拼装单个候选人的主表白名单字段 + age 回填 + 敏感(可选) + extra。

    等价原 build_candidate_snapshot 的内存拼装部分 (L77-109)，抽出便于批量复用，行为零变化
    (snapshot 仅在内存拼装，不写回 DB)。age 回填使 AtomicMetric(candidate.age) 真实可用，
    避免「指标可定义但永远算不出」的假绿。
    """
    node: Dict[str, Any] = {}
    for field, _label, _dtype in BASIC_FIELDS:
        node[field] = _jsonable(getattr(candidate, field, None))

    # age 字段回填：主表 age 为空时按 birth_date 实时计算年龄（岁，整数）。
    if node.get('age') in (None, '', 0):
        birth_date = getattr(candidate, 'birth_date', None)
        if birth_date is not None:
            try:
                from datetime import date
                today = date.today()
                node['age'] = today.year - birth_date.year - (
                    (today.month, today.day) < (birth_date.month, birth_date.day)
                )
            except Exception as e:  # noqa: BLE001 — 年龄计算失败不阻断快照 (按规则解析失败处理, 字段缺失降级)
                logger.warning('candidate_snapshot age 回填失败 candidate=%s: %s', getattr(candidate, 'pk', None), e, exc_info=True)

    if include_sensitive:
        for field in SENSITIVE_FIELDS:
            if hasattr(candidate, field):
                node[field] = _jsonable(getattr(candidate, field, None))

    # extra JSONField 展开（业务结构化数据入口，如 workExperience / education）
    extra = getattr(candidate, 'extra', None)
    if isinstance(extra, dict):
        for key, value in extra.items():
            if key in SENSITIVE_FIELDS and not include_sensitive:
                continue
            node.setdefault(key, value)

    return node


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
    except Exception as e:  # noqa: BLE001 — dynamic_field 字段路径枚举失败返空 list (降级, 主流程不缺该数据继续)
        logger.warning('candidate_snapshot 动态字段路径枚举失败: %s', e, exc_info=True)

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
    except Exception as e:  # noqa: BLE001 — 标量转换失败保留原值 (容错, MetricEngine 比较时会再处理)
        logger.warning('candidate_snapshot Decimal 标量转换失败: %s', e, exc_info=True)
    return value


# ---------------------------------------------------------------------------
# 需求 / 职位 快照（让 demand.* / position.* 对象路径指标可真实求值）
# ---------------------------------------------------------------------------
# 与候选人快照一致：只取非关系标量字段，排除审计字段与大字段，避免把关系/JSON
# 塞进规则上下文导致点路径解析失败或数据膨胀。
_ENTITY_SKIP_FIELDS = {
    'created_at', 'updated_at', 'deleted_at', 'created_by_id', 'updated_by_id',
}


def _entity_node(instance, model) -> Dict[str, Any]:
    """把一个模型实例的非关系标量字段组装成快照节点（对齐 build_candidate_snapshot）。"""
    node: Dict[str, Any] = {}
    for f in model._meta.fields:
        itype = f.get_internal_type()
        if itype in ('ForeignKey', 'OneToOneField', 'ManyToManyField',
                     'JSONField', 'FileField', 'ImageField', 'BinaryField'):
            continue
        if f.name in _ENTITY_SKIP_FIELDS:
            continue
        node[f.name] = _jsonable(getattr(instance, f.name, None))
    return node


def build_demand_snapshot(demand_id: str) -> Dict[str, Any]:
    """组装需求快照 `{'demand': {...}}`，供 `demand.*` 对象路径指标求值。

    需求不存在返回 `{'demand': {}}`（不抛异常，交由引擎判"字段解析失败"）。
    """
    from apps.demand.models import Demand

    obj = Demand.objects.filter(pk=demand_id).first()
    if obj is None:
        return {'demand': {}}
    return {'demand': _entity_node(obj, Demand)}


def build_position_snapshot(position_id: str) -> Dict[str, Any]:
    """组装职位快照 `{'position': {...}}`，供 `position.*` 对象路径指标求值。

    职位不存在返回 `{'position': {}}`（不抛异常，交由引擎判"字段解析失败"）。
    """
    from apps.position.models import Position

    obj = Position.objects.filter(pk=position_id).first()
    if obj is None:
        return {'position': {}}
    return {'position': _entity_node(obj, Position)}
