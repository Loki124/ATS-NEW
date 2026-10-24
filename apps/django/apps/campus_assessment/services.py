"""考核域取数与聚合（把 ranking.py 的纯公式接到数据库上）。

口径来源：契约 §2.2（端点）/ §2.3（排名算法）；逆向清单 §4.3 与 §5。

**可见范围**（契约 §1.3）：所有列表/排名/统计一律先经
`apps.campus_control.visibility.visible_persons(request.user)` 收窄 ——
超管见全部、班主任见本班、导师见徒弟、HRBP 见归属范围、校招生见本人。
本模块是**唯一**的收窄入口，视图只调这里，避免各处各写一套过滤条件。
"""
from datetime import date as date_cls
from datetime import time as time_cls
from decimal import Decimal

from django.apps import apps as django_apps
from django.db.models import Avg, Sum

from apps.campus_control.visibility import visible_persons

from . import ranking as R
from .models import (
    AttendanceMonthly,
    AttendanceRecord,
    FeedbackRecord,
    FiveForceScore,
    MonthlyAssessment,
)

#: 反馈处理状态取值（逆向清单 §4.3「反馈记录」状态机：处理中 → 已解决 / 已闭环）
STATUS_CLOSED = '已闭环'
STATUS_RESOLVED = '已解决'
STATUS_PROCESSING = '处理中'

#: 在校口径（契约 §1.3 排名范围）：**排除已离职**
PERSON_STATUS_RESIGNED = '离职'

#: 排序用的「最大时刻」（无打卡时间的记录排在最后）
_MAX_TIME = time_cls.max


def _minutes_of_day(value):
    """时刻换算成「当日第几分钟」（datetime.time 之间不能直接相减）。"""
    return value.hour * 60 + value.minute + value.second / 60


# ---------------------------------------------------------------------------
# 可见范围
# ---------------------------------------------------------------------------
def visible_person_qs(user, *, in_service_only=False):
    """当前用户可见的校招生 queryset（已过滤软删）。"""
    qs = visible_persons(user)
    if in_service_only:
        qs = qs.exclude(status=PERSON_STATUS_RESIGNED)
    return qs


def visible_person_ids(user, *, in_service_only=False):
    """当前用户可见的校招生 id 列表（供 `in` 过滤使用）。"""
    return list(visible_person_qs(user, in_service_only=in_service_only).values_list('id', flat=True))


# ---------------------------------------------------------------------------
# 兄弟 app（campus_learning）取值 —— 防御式取模型，未上线时降级为「无该维度」
# ---------------------------------------------------------------------------
def _optional_model(app_label, model_name):
    """取兄弟 app 的模型；app 未安装 / 模型不存在时返回 None（不抛错）。

    为什么防御式：`campus_learning` 与本 app 是**并行任务**（契约 §0 三 app 并行落地），
    学习/考试/活动数据是「学习成长」「附加分」两个维度的输入。
    app 未就绪时该维度按「无数据」处理，而不是让整个排名接口 500。
    """
    try:
        return django_apps.get_model(app_label, model_name)
    except LookupError:
        return None


def _learning_inputs(person_ids):
    """按人取学习相关的两个均值：课程进度均值（0~100）与考试得分均值。

    🔴 **必须按人分组**（契约 §2.3 + 逆向清单 A4）：
    A4 的口径是「**该人**的课程进度均值」与「**该人**的考试得分均值」，
    而**不是**全体人员的全局均值。

    早期实现先按人聚出每人的 `Avg`，再对**全体可见人员**求平均、返回**单个标量**，
    并在 `collect_dimensions` 的逐人循环里把同一个标量赋给**每一个人** ——
    这会**抹平个体差异**：学习成长维度对所有人相同 → A3 综合得分里 30% 的权重项
    退化成常数 → 综合排名失真、`?dim=learn` 视图全员并列第 1、班主任 `rankAvg.learn`
    恒为 1。库内学习数据为 0 时该缺陷**不显形** —— 那是未爆的地雷，不是「没问题」。

    Args:
        person_ids: 参与计算的人员 id 列表。

    Returns:
        `(course_avgs, exam_avgs)` —— 两个 `{person_id: 均值}` 字典。
        没有记录的人**不在字典里**（调用方取不到 → 「无记录」→ None，不是 0 分）。
    """
    course_avgs = {}
    exam_avgs = {}

    if not person_ids:
        return course_avgs, exam_avgs

    progress_model = _optional_model('campus_learning', 'LearnProgress')
    if progress_model is not None:
        rows = progress_model.objects.filter(person_id__in=person_ids).values('person_id').annotate(v=Avg('progress'))
        course_avgs = {r['person_id']: r['v'] for r in rows if r['v'] is not None}

    score_model = _optional_model('campus_learning', 'ExamScore')
    if score_model is not None:
        rows = score_model.objects.filter(person_id__in=person_ids).values('person_id').annotate(v=Avg('score'))
        exam_avgs = {r['person_id']: r['v'] for r in rows if r['v'] is not None}

    return course_avgs, exam_avgs


def _activity_rewards(person_ids):
    """活动奖励分值（逆向清单 A6）：`ActivityScore.reward` 文本里的整数。"""
    score_model = _optional_model('campus_learning', 'ActivityScore')
    if score_model is None or not person_ids:
        return {}
    rewards = {}
    rows = score_model.objects.filter(person_id__in=person_ids).values_list('person_id', 'reward')
    for person_id, reward in rows:
        rewards.setdefault(person_id, []).append(R.parse_reward(reward))
    return rewards


# ---------------------------------------------------------------------------
# 各维度取值
# ---------------------------------------------------------------------------
def _monthly_rows(person_ids, ym=None):
    """月度考核行（只取**已核对**的 —— 逆向清单 §4.3「核对通过…计入排名」）。"""
    if not person_ids:
        return {}
    qs = MonthlyAssessment.objects.filter(
        person_id__in=person_ids,
        status=MonthlyAssessment.Status.CHECKED,
    )
    if ym:
        qs = qs.filter(ym=ym)
    grouped = {}
    for row in qs:
        grouped.setdefault(row.person_id, []).append(row)
    return grouped


def _latest_five_force(person_ids):
    """每人**最近一次**五行五力评分（契约未定义多次评分口径，取最新）。"""
    if not person_ids:
        return {}
    qs = FiveForceScore.objects.filter(person_id__in=person_ids).order_by('person_id', '-scored_at', '-created_at')
    latest = {}
    for row in qs:
        latest.setdefault(row.person_id, row)
    return latest


def _attendance_rows(person_ids, ym=None):
    """月度考勤汇总行。"""
    if not person_ids:
        return {}
    qs = AttendanceMonthly.objects.filter(person_id__in=person_ids)
    if ym:
        qs = qs.filter(ym=ym)
    grouped = {}
    for row in qs:
        grouped.setdefault(row.person_id, []).append(row)
    return grouped


def collect_dimensions(person_ids, ym=None):
    """算每个人的各维度取值。

    Returns:
        `{person_id: {'total','kpi','exam','learn','force','add','attend','comp'}}`
        —— `total`=累计综合均分(A2)、`kpi`=KPI维度、`exam`=月度考试均值、
        `learn`=学习成长(A4)、`force`=五行五力(A5)、`add`=附加分(A6)、
        `attend`=考勤维度(A9)、`comp`=综合得分(A3)。
        无数据的维度为 None（表示「没有记录」，不是 0 分）。
    """
    person_ids = list(person_ids or [])
    monthly = _monthly_rows(person_ids, ym=ym)
    forces = _latest_five_force(person_ids)
    attendances = _attendance_rows(person_ids, ym=ym)
    course_avgs, exam_avgs = _learning_inputs(person_ids)
    rewards = _activity_rewards(person_ids)

    result = {}
    for person_id in person_ids:
        rows = monthly.get(person_id, [])
        total_scores = [R.monthly_total_score(r.kpi, r.exam, r.adjust) for r in rows]
        kpis = [r.kpi for r in rows]
        exams = [r.exam for r in rows]
        adjusts = [r.adjust for r in rows]

        force_row = forces.get(person_id)
        force_value = R.dim_force(force_row.dimension_values) if force_row else None

        add_value = R.dim_add(rewards.get(person_id, []), adjusts)

        # 学习成长（A4）：**该人自己的**课程进度均值与考试得分均值，
        # 「有哪项算哪项」；两项都没有 → None（「无记录」，不是 0 分）。
        # ⚠️ 这里必须用「按人」的均值，不能用全体人员的全局均值 ——
        #    全局化会把所有人的学习成长算成同一个数（详见 `_learning_inputs` 的注释）。
        learn_value = R.dim_learn(
            course_avgs.get(person_id),
            exam_avgs.get(person_id),
        )

        attend_value = R.attendance_dim([
            {'attend_days': r.attend_days, 'late_count': r.late_count}
            for r in attendances.get(person_id, [])
        ])

        kpi_value = R.dim_kpi(kpis)
        exam_value = R.js_round(sum(exams) / len(exams), 1) if exams else None

        result[person_id] = {
            'total': R.avg_total(total_scores),
            'kpi': kpi_value,
            'exam': exam_value,
            'learn': learn_value,
            'force': force_value,
            'add': add_value,
            'attend': attend_value,
            'comp': R.composite_score(kpi_value, learn_value, force_value, add_value),
        }
    return result


# ---------------------------------------------------------------------------
# 名次
# ---------------------------------------------------------------------------
def rank_map(rows, value_key):
    """按 `rows[i][value_key]` 降序算名次 → `{row_id: rank}`。

    并列名次用标准 1224 口径（同分同名次，后续名次跳过占位）。
    缺数据（None）排在最后（无数据 ≠ 0 分，但不能靠「没数据」挤进前列）。
    """
    def sort_key(row):
        value = row.get(value_key)
        if value is None:
            return (1, Decimal(0))
        return (0, -Decimal(value))

    ordered = sorted(rows, key=sort_key)
    ranks = {}
    prev_value = None
    prev_rank = 0
    has_prev = False
    for idx, row in enumerate(ordered, start=1):
        value = row.get(value_key)
        if has_prev and value is not None and prev_value is not None and Decimal(value) == Decimal(prev_value):
            ranks[row['id']] = prev_rank
        else:
            ranks[row['id']] = idx
            prev_rank = idx
        prev_value = value
        has_prev = True
    return ranks


# ---------------------------------------------------------------------------
# 综合排名
# ---------------------------------------------------------------------------
#: dim 取值 → 中文名（契约 §2.2：`?dim=comp|kpi|learn|force|add`）
DIM_LABELS = {
    'comp': '综合',
    'kpi': 'KPI',
    'learn': '学习成长',
    'force': '五行五力',
    'add': '附加分',
}

#: dim → 折算得分权重（逆向清单 §4.3「表格同时展示实际值与折算得分」）
DIM_WEIGHTS = {
    'comp': None,       # 综合分本身就是加权结果
    'kpi': Decimal('0.5'),
    'learn': Decimal('0.3'),
    'force': Decimal('0.2'),
    'add': None,        # 附加分全额计入
}


def _dim_score(dim, value):
    """按维度给「折算得分」。"""
    if value is None:
        return None
    weight = DIM_WEIGHTS.get(dim)
    if weight is None:
        return value if dim == 'comp' else value
    return R.js_round(Decimal(value) * weight)


def composite_ranking(user, dim='comp', ym=None, class_filter=None):
    """综合排名（契约 §2.2 `ranking/composite/`）。

    Args:
        user: 当前登录用户（可见范围收窄）。
        dim: comp / kpi / learn / force / add —— 切换排序维度。
        ym: 限定考核月份（YYYY-MM），为空则用全部月份。
        class_filter: 班级过滤（班级 id 或班级编号）。

    Returns:
        `{'dim': ..., 'ym': ..., 'class': ..., 'dims': [...], 'list': [...]}`。
    """
    dim = dim if dim in DIM_LABELS else 'comp'
    persons = visible_person_qs(user, in_service_only=True)
    if class_filter:
        persons = filter_persons_by_class(persons, class_filter)

    person_list = list(persons)
    person_ids = [p.id for p in person_list]
    dims = collect_dimensions(person_ids, ym=ym)

    rows = []
    for person in person_list:
        values = dims.get(person.id, {})
        rows.append({
            'id': person.id,
            'name': person.name,
            'code': person.code,
            'bu': person.bu,
            'class_name': person.class_room.name if person.class_room_id else '',
            'class_code': person.class_room.code if person.class_room_id else '',
            'total': values.get('total'),
            'kpi': values.get('kpi'),
            'exam': values.get('exam'),
            'learn': values.get('learn'),
            'force': values.get('force'),
            'add': values.get('add'),
            'attend': values.get('attend'),
            'comp': values.get('comp'),
        })

    ranks = rank_map(rows, dim)
    result_rows = []
    for row in sorted(rows, key=lambda r: (ranks[r['id']], r['name'])):
        result_rows.append({
            'rank': ranks[row['id']],
            'person_id': row['id'],
            'name': row['name'],
            'code': row['code'],
            'bu': row['bu'],
            'class_name': row['class_name'],
            'class_code': row['class_code'],
            'total': row['total'],
            'kpi': row['kpi'],
            'exam': row['exam'],
            'learn': row['learn'],
            'force': row['force'],
            'add': row['add'],
            'attend': row['attend'],
            'comp': row['comp'],
            # 「实际值」= 该维度的原始取值；「折算得分」= 该维度计入综合分时的贡献
            'dim_value': row.get(dim),
            'dim_score': _dim_score(dim, row.get(dim)),
        })

    return {
        'dim': dim,
        'dim_label': DIM_LABELS[dim],
        'ym': ym or '',
        'class': class_filter or '',
        'dims': list(DIM_LABELS.keys()),
        'list': result_rows,
    }


def filter_persons_by_class(queryset, class_filter):
    """按班级过滤人员 queryset：`class_filter` 可以是班级 id，也可以是班级编号（code）。

    「?class=」是契约 §2.2 明确列出的筛选项，但没规定传什么 → 两种都支持：
    传 id 按主键过滤，传编号按 `ClassRoom.code` 过滤（前端表格里展示的是班级编号）。
    """
    value = str(class_filter).strip()
    if not value:
        return queryset
    from apps.campus_rotation.models import ClassRoom

    classroom = ClassRoom.objects.filter(id=value).first()
    if classroom is not None:
        return queryset.filter(class_room_id=classroom.id)
    return queryset.filter(class_room__code=value)


# ---------------------------------------------------------------------------
# 班主任排名
# ---------------------------------------------------------------------------
#: 班主任排名要统计的五个维度名次（逆向清单 §4.3：综合/KPI/考试/学习/考勤）
TEACHER_RANK_DIMS = (
    ('total', '综合'),
    ('kpi', 'KPI'),
    ('exam', '考试'),
    ('learn', '学习'),
    ('attend', '考勤'),
)


def _teacher_of(person):
    """取校招生的班主任：优先人员档案上的班主任，回退到班级班主任。"""
    if person.head_teacher_id:
        return person.head_teacher
    if person.class_room_id and person.class_room.head_teacher_id:
        return person.class_room.head_teacher
    return None


def teacher_ranking(user):
    """班主任排名（契约 §2.2 `ranking/teacher/`）。

    口径（逆向清单 A8 / views2.js:128）：
    - `avgTotal` = 所带学生 avgTotal 的算术平均（1 位）；
    - `rankAvg[dim]` = 所带学生在该维度**名次**的算术平均（名次在全体在培范围内算）；
    - 班主任排序 = 所带学生累计综合均分（avgTotal）降序。

    可见范围：只统计**可见人员**构成的学生群体 —— 导师看到的只是自己徒弟所在班
    的聚合，不会泄露其他班主任的班级数据。
    """
    persons = list(visible_person_qs(user, in_service_only=True))
    person_ids = [p.id for p in persons]
    dims = collect_dimensions(person_ids)

    student_rows = []
    for person in persons:
        values = dims.get(person.id, {})
        teacher = _teacher_of(person)
        student_rows.append({
            'id': person.id,
            'name': person.name,
            'code': person.code,
            'bu': person.bu,
            'class_name': person.class_room.name if person.class_room_id else '',
            'class_code': person.class_room.code if person.class_room_id else '',
            'teacher_id': teacher.id if teacher else None,
            'total': values.get('total'),
            'kpi': values.get('kpi'),
            'exam': values.get('exam'),
            'learn': values.get('learn'),
            'force': values.get('force'),
            'add': values.get('add'),
            'attend': values.get('attend'),
            'comp': values.get('comp'),
        })

    # 名次：综合 / KPI / 考试 / 学习 / 考勤（全体在培范围内算）
    ranks = {}
    for key, _label in TEACHER_RANK_DIMS:
        source_key = 'comp' if key == 'total' else key
        ranks[key] = rank_map(student_rows, source_key)

    # 按班主任聚合
    teachers = {}
    for row in student_rows:
        teacher_id = row['teacher_id']
        if not teacher_id:
            continue
        bucket = teachers.setdefault(teacher_id, {'teacher_id': teacher_id, 'students': []})
        bucket['students'].append(row)

    from apps.core.models import User

    teacher_rows = []
    for teacher_id, bucket in teachers.items():
        students = bucket['students']
        avg_total = R.teacher_avg_total([s['total'] for s in students])
        rank_avg = {}
        for key, _label in TEACHER_RANK_DIMS:
            rank_avg[key] = R.teacher_rank_avg([ranks[key].get(s['id']) for s in students])
        teacher = User.objects.filter(pk=teacher_id).first()
        teacher_rows.append({
            'teacher_id': teacher_id,
            'name': teacher.full_name if teacher else '',
            'student_count': len(students),
            'avg_total': avg_total,
            'rank_avg': rank_avg,
        })

    teacher_rows.sort(key=lambda t: (
        -(t['avg_total'] if t['avg_total'] is not None else Decimal('-1e9')),
        t['name'],
    ))
    teacher_ranks = R.competition_ranks([t['avg_total'] for t in teacher_rows])
    for idx, row in enumerate(teacher_rows):
        row['rank'] = teacher_ranks[idx]

    # 学生分项名次明细
    student_detail = []
    for row in sorted(student_rows, key=lambda r: (ranks['total'].get(r['id'], 0), r['name'])):
        student_detail.append({
            'person_id': row['id'],
            'name': row['name'],
            'code': row['code'],
            'bu': row['bu'],
            'class_name': row['class_name'],
            'class_code': row['class_code'],
            'teacher_id': row['teacher_id'],
            'total': row['total'],
            'kpi': row['kpi'],
            'exam': row['exam'],
            'learn': row['learn'],
            'attend': row['attend'],
            'comp': row['comp'],
            'ranks': {key: ranks[key].get(row['id']) for key, _label in TEACHER_RANK_DIMS},
        })

    return {
        'dims': [{'key': key, 'label': label} for key, label in TEACHER_RANK_DIMS],
        'teachers': teacher_rows,
        'students': student_detail,
    }


# ---------------------------------------------------------------------------
# 当日打卡排名
# ---------------------------------------------------------------------------
def daily_attendance_ranking(user, day=None):
    """当日打卡排名（契约 §2.2 `attendance-records/daily-ranking/`）。

    ⚠️ **口径说明（逆向清单该视图在目标站被清空，无原始实现可对齐）**：
    本实现按「打卡时间先后」排名（同刻并列同名次），并给出「与第1名差距」
    （与当日最早打卡时间的分钟差）。若后续拿到目标站原始口径，本函数是唯一改动点。

    仅统计**当日有打卡记录**的人员；范围与列表一致（可见人员）。
    """
    day = day or date_cls.today()
    person_ids = visible_person_ids(user, in_service_only=True)
    if not person_ids:
        return {'date': day.isoformat(), 'list': []}

    records = AttendanceRecord.objects.filter(
        person_id__in=person_ids, date=day,
    )

    from apps.campus_control.models import Person

    person_map = {p.id: p for p in Person.objects.filter(id__in=person_ids).select_related('class_room')}

    rows = []
    for record in records:
        person = person_map.get(record.person_id)
        rows.append({
            'id': record.person_id,
            'name': person.name if person else '',
            'code': person.code if person else '',
            'class_name': person.class_room.name if person and person.class_room_id else '',
            'class_code': person.class_room.code if person and person.class_room_id else '',
            'punch_time': record.punch_time,
            'status': record.status,
            'remark': record.remark,
        })

    # 打卡时间升序（早的在前）；无打卡时间的排最后
    rows.sort(key=lambda r: (r['punch_time'] is None, r['punch_time'] or _MAX_TIME, r['name']))

    # 名次：打卡时间相同 → 并列（1224 口径）；无打卡时间的一组也并列
    ranks = []
    prev_time = None
    prev_rank = 0
    prev_is_none = None
    for idx, row in enumerate(rows, start=1):
        punch = row['punch_time']
        is_none = punch is None
        if prev_is_none is not None and is_none == prev_is_none and (is_none or punch == prev_time):
            ranks.append(prev_rank)
        else:
            ranks.append(idx)
            prev_rank = idx
        prev_time = punch
        prev_is_none = is_none

    first_time = rows[0]['punch_time'] if rows else None
    result = []
    for idx, row in enumerate(rows):
        gap_minutes = None
        gap_text = ''
        if row['punch_time'] and first_time:
            # datetime.time 不能直接相减 → 换成「当日第几分钟」再算差值
            gap_minutes = int(_minutes_of_day(row['punch_time']) - _minutes_of_day(first_time))
            gap_text = '与第1名持平' if gap_minutes == 0 else f'落后第1名 {gap_minutes} 分钟'
        result.append({
            'rank': ranks[idx],
            'person_id': row['id'],
            'name': row['name'],
            'code': row['code'],
            'class_name': row['class_name'],
            'class_code': row['class_code'],
            'punch_time': row['punch_time'].isoformat() if row['punch_time'] else '',
            'status': row['status'],
            'remark': row['remark'],
            'gap_minutes': gap_minutes,
            'gap_text': gap_text,
        })

    return {'date': day.isoformat(), 'list': result}


# ---------------------------------------------------------------------------
# 统计概览
# ---------------------------------------------------------------------------
def stats_overview(user, ym=None):
    """4 卡统计 + 考勤汇总（契约 §2.2 `stats/overview/`）。

    4 卡（逆向清单 §4.3「反馈记录」）：总数 / 处理中 / 已解决·已闭环 / 含证据记录。
    考勤：出勤·迟到·请假汇总。
    """
    person_ids = visible_person_ids(user)

    feedback_qs = FeedbackRecord.objects.filter(person_id__in=person_ids) if person_ids \
        else FeedbackRecord.objects.none()
    total = feedback_qs.count()
    processing = feedback_qs.filter(status=STATUS_PROCESSING).count()
    resolved = feedback_qs.filter(status=STATUS_RESOLVED).count()
    closed = feedback_qs.filter(status=STATUS_CLOSED).count()
    with_evidence = feedback_qs.exclude(attachments=[]).count()

    attend_qs = AttendanceMonthly.objects.filter(person_id__in=person_ids) if person_ids \
        else AttendanceMonthly.objects.none()
    if ym:
        attend_qs = attend_qs.filter(ym=ym)
    attend_sum = attend_qs.aggregate(
        attend_days=Sum('attend_days'), late_count=Sum('late_count'), leave_days=Sum('leave_days'),
    )

    return {
        'feedback': {
            'total': total,
            'processing': processing,
            'resolved': resolved,
            'closed': closed,
            'resolved_total': resolved + closed,
            'with_evidence': with_evidence,
        },
        'attendance': {
            'attend_days': attend_sum['attend_days'] or 0,
            'late_count': attend_sum['late_count'] or 0,
            'leave_days': attend_sum['leave_days'] or 0,
        },
        'ym': ym or '',
    }
