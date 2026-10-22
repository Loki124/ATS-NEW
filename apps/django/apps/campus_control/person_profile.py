"""校招生档案详情（个人档案）聚合服务 — 2026-10-21 二期。

一次请求返回「个人档案」详情弹窗所需的全部数据，避免前端 N 次串行请求：

    GET /api/v1/campus/persons/{id}/profile/
    → { success: true, data: { person, class_room, rotation, stats,
                                stages, monthly_assessments, daily_reports,
                                recommendations, feedbacks } }

## 一、数据来源与关联口径

- 档案主体：`campus_control.Person`（一行一人）。
- 班级：`Person.class_room` → `campus_rotation.ClassRoom`（含班主任 / HRBP / 批次）。
- 轮岗安排：`campus_rotation.RotationArrangement`。
  🔴 关联口径**优先** `RotationArrangement.campus_person` == `Person.id`
  （2026-10-22 新增的人员级 nanoid 关联，唯一可靠口径）；**回退**旧口径
  `RotationArrangement.person_id` == `Person.user_id`（BigInteger 账号 id）。
  `Person.user_id` 为空时旧口径查不到轮岗记录 —— 有 `campus_person` 关联则照常显示。
- 轮岗期考核结果：`RotationStage`（按 arrangement 关联，每段独立考核）。

## 二、尚未建模的四个业务域

「轮岗期月度考核明细 / 日报及评价 / 推介意见 / 反馈记录」四个业务域在本期
**尚无对应数据模型**（apps/campus_rotation 无相关表）。此处一律返回空数组，
由前端渲染空态（与设计稿「暂无数据」一致）；模型落地后只需在此处补充装配逻辑，
前端无需改动。

## 三、统计口径（默认约定，可按业务口径调整）

- 轮岗均分：该生全部轮岗期 `RotationStage.score` 的算术平均（无评分时为 None）。
- 综合评分：当前口径 = 轮岗均分（月度考核未建模，暂不参与加权）。
- 综合排名：取最新一条轮岗安排的 `rank`（无则为 None）。
- 综合评级：由综合评分分档（≥90 优秀 / ≥80 良好 / ≥60 合格 / 其余 待改进），
  无评分时为 None（前端显示「—」，不臆造 0 分）。
"""
from decimal import Decimal

from apps.campus_rotation.models import RotationArrangement, RotationStage

# 轮岗安排阶段的展示名（RotationArrangementStage.choices）
_STAGE_LABELS = {
    'PENDING': '待分配',
    'APPROVING': '审批中',
    'ONGOING': '轮岗中',
    'DONE': '已完成',
    'TERMINATED': '已终止',
}

# 轮岗期考核状态的展示名（RotationStage.ASSESSMENT_CHOICES）
_ASSESSMENT_LABELS = {
    'PENDING': '未判定',
    'WAIVED': '免考',
    'REQUIRED': '需考核',
    'DONE': '已考核',
}

# 综合评级分档（默认口径，见模块 docstring §三）
_RATING_BUCKETS = (
    (Decimal('90'), '优秀'),
    (Decimal('80'), '良好'),
    (Decimal('60'), '合格'),
)
_RATING_FALLBACK = '待改进'


def _fmt_date(d):
    """日期 → 'YYYY-MM-DD'；空值返回 ''。"""
    return d.isoformat() if d else ''


def _fmt_period(start, end):
    """轮岗周期 → '2026-01-01 ~ 2026-03-31'；起止皆空返回 ''。"""
    if not start and not end:
        return ''
    return f'{_fmt_date(start)} ~ {_fmt_date(end)}'


def _bu_name(dept):
    """二级部门（BU）名：取该部门自身或其最近祖先中的 BU（0 基层级 depth==2）。

    口径与 `apps/core/dept_depth.py`（全仓唯一真相源）一致：
    根=0、事业群=1、BU=2、三级部门=3。
    ⚠️ 历史实现按「parent 存在且 parent.parent 为空」判定 = 第 1 级（事业群），
    与前端下拉（level===2）及 PRD 的 BU=2 差一级 —— 三级部门解析出来的「BU」
    实际是它的事业群。现改为走共享口径的 `bu_ancestor`。
    """
    from apps.core.dept_depth import bu_ancestor
    node = bu_ancestor(dept)
    return node.name if node is not None else ''


def _avg(values):
    """算术平均；空集合返回 None（不返回 0，避免把「无数据」表达成「0 分」）。"""
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums, 0.0) / len(nums)


def _rating(score):
    """综合评分 → 评级文案；无评分返回 None。"""
    if score is None:
        return None
    for threshold, label in _RATING_BUCKETS:
        if score >= threshold:
            return label
    return _RATING_FALLBACK


def _person_arrangements(person):
    """该生的轮岗安排，按创建时间倒序。

    关联口径（与 `person_rotation_stats.build_rotation_stats_map` **完全一致**，
    避免列表列与档案详情对不上）：
      ① `RotationArrangement.campus_person == Person.id`（人员级 nanoid，2026-10-22 起为唯一可靠口径）；
      ② 回退 `RotationArrangement.person_id == Person.user_id`（旧账号 id 口径，历史数据）。

    ⚠️ 旧实现只认口径 ② 且「无 user_id 直接返回空」→ 校招生普遍没有账号，
    档案详情的轮岗区段恒为空。现在口径 ① 优先，且无账号时**不再短路**。
    """
    from django.db.models import Q

    condition = Q(campus_person_id=person.id)
    if person.user_id:
        condition |= Q(person_id=person.user_id)
    return list(
        RotationArrangement.objects.filter(
            condition, deleted_at__isnull=True,
        ).select_related(
            'current_dept', 'mentor', 'head_teacher', 'class_room', 'direct_manager',
        ).order_by('-created_at')
    )


def _current_arrangement(arrangements):
    """当前轮岗安排：优先 ONGOING（轮岗中），其次最新一条。"""
    for a in arrangements:
        if a.stage == 'ONGOING':
            return a
    return arrangements[0] if arrangements else None


def _stage_rows(arrangements):
    """轮岗期考核结果：每个 RotationStage 一行，附其所属安排。"""
    if not arrangements:
        return []
    stages = RotationStage.objects.filter(
        arrangement__in=arrangements, deleted_at__isnull=True,
    ).select_related('department', 'mentor', 'assessed_by').order_by('stage_no', 'created_at')

    arrangement_by_id = {a.id: a for a in arrangements}
    rows = []
    for st in stages:
        arrangement = arrangement_by_id.get(st.arrangement_id)
        start = st.actual_start or st.planned_start
        end = st.actual_end or st.planned_end
        rows.append({
            'id': str(st.id),
            'arrangement_id': str(st.arrangement_id) if st.arrangement_id else '',
            'stage_no': st.stage_no,
            # 轮岗部门（阶段实际部门）
            'department': st.department.name if st.department_id else '',
            # 二级部门（BU）：阶段部门的深度 2 祖先
            'bu': _bu_name(st.department) if st.department_id else '',
            'period': _fmt_period(start, end),
            'planned_period': _fmt_period(st.planned_start, st.planned_end),
            'status': _ASSESSMENT_LABELS.get(st.assessment_status, st.assessment_status or ''),
            'assessment_status': st.assessment_status or '',
            'score': float(st.score) if st.score is not None else None,
            'result': st.assessment_result or '',
            'mentor': st.mentor.full_name if st.mentor_id else '',
            'mentor_id': str(st.mentor_id) if st.mentor_id else '',
            'arrangement_stage': _STAGE_LABELS.get(
                arrangement.stage, arrangement.stage) if arrangement else '',
            'assessed_at': st.assessed_at.isoformat() if st.assessed_at else '',
            'assessed_by': st.assessed_by.full_name if st.assessed_by_id else '',
        })
    return rows


def build_person_profile(person):
    """装配个人档案详情载荷（纯函数，无副作用）。

    :param person: campus_control.Person 实例
    :return: dict（键名 snake_case，API 边界由 camelCase 渲染器转换）
    """
    class_room = person.class_room
    arrangements = _person_arrangements(person)
    current = _current_arrangement(arrangements)
    stages = _stage_rows(arrangements)

    scores = [st.get('score') for st in stages]
    rotation_avg = _avg(scores)
    # 月度考核未建模 → 月度综合均分暂无口径，返回 None（前端显示「—」）
    monthly_avg = None
    overall = rotation_avg if rotation_avg is not None else monthly_avg
    rank = current.rank if current is not None else None

    person_payload = {
        'id': str(person.id),
        'code': person.code,
        'name': person.name,
        'employee_id': person.employee_id or '',
        'status': person.status or '',
        'sex': person.sex or '',
        'bu': person.bu or '',
        'position': person.position or '',
        'level': person.level or '',
        'school': person.school or '',
        'school_name': person.school_name or '',
        'major': person.major or '',
        'education': person.education or '',
        'phone': person.phone or '',
        'month': person.month or '',
        'expected_entry_date': _fmt_date(person.expected_entry_date),
        'actual_entry_date': _fmt_date(person.actual_entry_date),
        'counted': person.counted,
        'class_room_id': str(person.class_room_id) if person.class_room_id else '',
        'class_room_name': class_room.name if class_room else '',
        'head_teacher_id': str(person.head_teacher_id) if person.head_teacher_id else '',
        'head_teacher_name': person.head_teacher.full_name if person.head_teacher_id else '',
        'mentor_id': str(person.mentor_id) if person.mentor_id else '',
        'mentor_name': person.mentor.full_name if person.mentor_id else '',
        # 批次：取自所属班级（校招生按班级编批）
        'batch': (class_room.batch if class_room else '') or '',
    }

    class_room_payload = None
    if class_room:
        class_room_payload = {
            'id': str(class_room.id),
            'code': class_room.code,
            'name': class_room.name,
            'batch': class_room.batch or '',
            'head_teacher': class_room.head_teacher.full_name if class_room.head_teacher_id else '',
            'hrbp': class_room.hrbp.full_name if class_room.hrbp_id else '',
            # 班级在校招生数（口径与 ClassRoomSerializer.student_count 一致：
            # 该班级绑定的轮岗安排条数）
            'student_count': RotationArrangement.objects.filter(
                class_room_id=class_room.id,
            ).count(),
        }

    rotation_payload = None
    if current is not None:
        rotation_payload = {
            'id': str(current.id),
            'stage': current.stage or '',
            'stage_label': _STAGE_LABELS.get(current.stage, current.stage or ''),
            'current_dept': current.current_dept.name if current.current_dept_id else '',
            'current_dept_id': str(current.current_dept_id) if current.current_dept_id else '',
            'mentor': current.mentor.full_name if current.mentor_id else '',
            'mentor_id': str(current.mentor_id) if current.mentor_id else '',
            'head_teacher': current.head_teacher.full_name if current.head_teacher_id else '',
            'direct_manager': current.direct_manager.full_name if current.direct_manager_id else '',
            'class_room': current.class_room.name if current.class_room_id else '',
            'rotation_start': _fmt_date(current.rotation_start),
            'rotation_end': _fmt_date(current.rotation_end),
            'rank': current.rank,
            'result': current.result or '',
            'final_dept': current.final_dept or '',
            'note': current.note or '',
        }

    return {
        'person': person_payload,
        'class_room': class_room_payload,
        'rotation': rotation_payload,
        'stats': {
            'rotation_avg_score': rotation_avg,
            'monthly_avg_score': monthly_avg,
            'overall_score': overall,
            'rank': rank,
            'rating': _rating(overall),
        },
        'stages': stages,
        # 以下四个业务域暂无数据模型，统一返回空数组（前端渲染空态）
        'monthly_assessments': [],
        'daily_reports': [],
        'recommendations': [],
        'feedbacks': [],
    }
