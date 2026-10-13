"""候选人变更审计（CandidateHistory）基础设施。

设计要点：
- ``compute_row_hash`` 是**纯函数**（仅依赖 stdlib），模型的 ``save()`` 与迁移回填
  共用同一实现，保证哈希链口径一致。顶部不 import 任何 Django 模型，迁移期可安全 import。
- ``CandidateHistory`` 行**不可篡改**：模型 ``save()`` 在 INSERT 时自动补 ``seq`` 单调序号
  与 ``prev_hash``/``row_hash`` 哈希链；对既有行的 UPDATE / ``delete()`` 直接抛
  ``AuditImmutabilityError``。软删走 ``save()`` 亦被拦截。
- ``diff_fields`` / ``record_*`` 提供字段级 before→after diff 与各场景审计写入入口；
  内部统一走 ``CandidateHistory.objects.create``，由模型 ``save()`` 自动接哈希链。
"""
import hashlib
import json


class AuditImmutabilityError(Exception):
    """审计行不可修改/删除（不可篡改）。"""


def _canonical(value) -> str:
    """任意 JSON 结构的规范化字符串：键排序、紧凑分隔、保留中文、不可序列化对象退化为 str。"""
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)


def compute_row_hash(candidate_id, seq, action, detail, created_by_id, prev_hash) -> str:
    """行内容 → sha256 十六进制。刻意**不含 created_at**（auto_now_add 会在 save 时覆盖，
    纳入会导致哈希与落库值不一致）；防篡改覆盖 action/detail/actor 与 prev_hash 链。"""
    payload = '|'.join([
        str(candidate_id or ''),
        str(seq or 0),
        str(action or ''),
        _canonical(detail or {}),
        str(created_by_id or ''),
        str(prev_hash or ''),
    ])
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def jsonable(value):
    """把模型字段值转为可 JSON 序列化、可稳定比较的形式（Decimal/date/datetime→str）。"""
    if value is None:
        return None
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


# 模型列中文标签（基本信息更新 diff 的 label 来源）
FIELD_LABELS = {
    'name': '姓名', 'phone': '手机号', 'email': '邮箱', 'gender': '性别',
    'age': '年龄', 'birth_date': '出生日期', 'id_card_no': '身份证号',
    'highest_education': '最高学历', 'work_years': '工作年限',
    'current_city': '当前城市', 'expected_city': '期望城市',
    'current_company': '当前公司', 'current_position': '当前职位',
    'expected_salary': '期望薪资', 'resume_file_url': '简历文件',
    'resume_text': '简历文本', 'tags': '标签', 'extra': '扩展信息',
    'resume_score': '简历评分', 'source_channel': '来源渠道', 'referrer': '推荐人',
    'recruiter': '招聘负责人', 'is_archived': '是否归档',
}


def diff_fields(old_snapshot: dict, new_snapshot: dict, fields) -> list:
    """逐字段比对，返回 ``[{field, label, old, new}]``（仅含发生变化的字段）。"""
    changes = []
    for f in fields:
        old = jsonable((old_snapshot or {}).get(f))
        new = jsonable((new_snapshot or {}).get(f))
        if old != new:
            changes.append({'field': f, 'label': FIELD_LABELS.get(f, f), 'old': old, 'new': new})
    return changes


# 与 CandidateUpdateSerializer.Meta.fields 对齐（基本信息 / 简历附件可改字段）。
# 若序列化器字段调整，需同步此列表（diff 的字段面）。
CANDIDATE_UPDATABLE_FIELDS = [
    'email', 'gender', 'age', 'birth_date', 'id_card_no',
    'highest_education', 'work_years',
    'current_city', 'expected_city', 'current_company', 'current_position',
    'expected_salary', 'resume_file_url', 'resume_text',
    'tags', 'extra',
]
# 简历文件/文本：单独归为 RESUME_UPLOADED，便于「上传后的内容」溯源
RESUME_FILE_FIELDS = ('resume_file_url', 'resume_text')


def _actor_id(actor):
    return getattr(actor, 'id', None) if (actor and getattr(actor, 'is_authenticated', False)) else None


def _create(candidate, action: str, detail: dict, actor=None):
    from .models import CandidateHistory  # 延迟导入：保证本模块顶部无模型依赖
    return CandidateHistory.objects.create(
        candidate=candidate,
        action=action,
        detail=detail or {},
        created_by=actor if _actor_id(actor) else None,
    )


def record_info_update(candidate, changes: list, actor=None, source: str = 'api'):
    """基本信息 / 简历附件字段更新（字段级 before→after）。"""
    if not changes:
        return None
    return _create(candidate, 'INFO_UPDATED', {'changes': changes, 'source': source}, actor)


def record_resume_fields_update(candidate, changes: list, actor=None):
    """简历扩展字段（CandidateFieldValue）更新（字段级 before→after）。"""
    if not changes:
        return None
    return _create(candidate, 'RESUME_FIELDS_UPDATED', {'changes': changes, 'source': 'api'}, actor)


def record_resume_uploaded(candidate, changes: list, actor=None):
    """简历文件/文本替换（上传后的内容变更）。changes 为 resume_file_url/resume_text 子集。"""
    if not changes:
        return None
    return _create(candidate, 'RESUME_UPLOADED', {'changes': changes, 'source': 'api'}, actor)


def record_created(candidate, actor=None, source: str = 'api'):
    """候选人创建（含 add_candidate 批量入库路径，该路径绕过 create_candidate）。"""
    return _create(candidate, 'CREATED', {'source': source}, actor)


def record_resume_parsed(candidate, parse_info: dict, actor=None):
    """简历解析入库溯源（初始解析数据）。parse_info 含 job_id/file_name/provider/confidence 等。"""
    return _create(candidate, 'RESUME_PARSED', {'parse': parse_info, 'source': 'add_candidate'}, actor)


def record_stage_change(application, from_stage, to_stage, actor=None, via: str = 'advance'):
    """投递阶段（Application.current_stage）变更 —— 跨 app 写候选人维度审计。"""
    # 阶段未实质变化（如升版本落点相同）则不记，避免噪声
    if from_stage and to_stage and from_stage == to_stage:
        return None
    candidate = application.candidate
    position = getattr(application, 'position', None)
    detail = {
        'application_id': application.id,
        'application_code': getattr(application, 'code', None),
        'position': getattr(position, 'title', None) if position else None,
        'from_stage': from_stage,
        'to_stage': to_stage,
        'via': via,
    }
    return _create(candidate, 'STAGE_CHANGED', detail, actor)
