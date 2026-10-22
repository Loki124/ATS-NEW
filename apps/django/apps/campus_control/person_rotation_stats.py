"""人员列表的轮岗维度批量聚合（2026-10-22 兵哥指令：列表新增「轮岗状态 / 当前轮岗部门 / 综合评分」）。

## 为什么要单独抽模块

列表要按页下发三个轮岗维度指标，若在序列化器里逐行查轮岗安排 + 轮岗期考核，
200 行就是 400 次查询（N+1）。本模块按**整页人员一次性批量聚合**，
结果经 ViewSet 的 serializer context 交给序列化器渲染。

## 口径（与个人档案详情 `person_profile.py` **完全一致**，避免列表与详情对不上）

- 关联：**优先 `RotationArrangement.campus_person == Person.id`**（人员级 nanoid 口径，
  2026-10-22 新增）；旧数据回退 `RotationArrangement.person_id == Person.user_id`
  （BigInteger 账号 id 口径；dev 库里校招生基本没有账号 → 该口径查不到任何安排）。
- 当前轮岗安排：优先 `ONGOING`（轮岗中），其次按创建时间倒序取最新一条。
- 轮岗状态：当前安排的 `stage`（同时给出 code 与中文标签）。
- 当前轮岗部门：当前安排的 `current_dept` 名；**无安排时回退 `Person.bu`**
  （Person.bu 的模型注释即「现在轮岗在哪个部门」）。
- 综合评分：该生**全部**轮岗安排下所有轮岗期 `RotationStage.score` 的算术平均；
  无评分时返回 `None`（**不返回 0** ——「无数据」不等于「0 分」，前端显示「—」）。
"""
from django.db.models import Q

from apps.campus_rotation.models import RotationArrangement, RotationStage

# 轮岗安排阶段的展示名（与 apps/campus_rotation.models.RotationArrangementStage.choices 同源）
STAGE_LABELS = {
    'PENDING': '待分配',
    'APPROVING': '审批中',
    'ONGOING': '轮岗中',
    'DONE': '已完成',
    'TERMINATED': '已终止',
}

# 合法的轮岗状态 code 集合（过滤参数白名单，防传入非法值触发全表扫描或报错）
STAGE_CODES = tuple(STAGE_LABELS.keys())


def _avg(values):
    """算术平均；空集合返回 None（不返回 0，避免把「无数据」表达成「0 分」）。"""
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    return sum(nums, 0.0) / len(nums)


def _empty_entry(person):
    return {
        'rotation_status': '',
        'rotation_status_label': '',
        'rotation_dept': person.bu or '',
        'overall_score': None,
    }


def build_rotation_stats_map(persons):
    """批量聚合一页人员的轮岗维度指标。

    :param persons: Person 实例序列（通常是当前分页页内的对象）
    :return: {person_id(str): {'rotation_status', 'rotation_status_label',
                                'rotation_dept', 'overall_score'}}
    """
    persons = list(persons)
    if not persons:
        return {}

    result = {str(p.id): _empty_entry(p) for p in persons}
    user_ids = [p.user_id for p in persons if p.user_id]
    person_ids = [p.id for p in persons]

    # 一次取回本页全部人员的轮岗安排（人员级口径优先，旧账号口径回退）
    #   campus_person：Person 主键 nanoid（可靠口径）
    #   person_id     ：旧 BigInteger 账号 id 口径（历史数据回退）
    arrangements = list(
        RotationArrangement.objects.filter(
            Q(campus_person_id__in=person_ids) | Q(person_id__in=user_ids),
            deleted_at__isnull=True,
        ).select_related('current_dept', 'campus_person').order_by('-created_at')
    )
    by_person = {}
    for a in arrangements:
        # 归组键统一成 Person 主键（nanoid）；旧口径要用 Person.user_id 反查
        if a.campus_person_id:
            key = a.campus_person_id
        else:
            key = next((p.id for p in persons if p.user_id == a.person_id), None)
        if key:
            by_person.setdefault(key, []).append(a)

    # 当前安排：优先 ONGOING（轮岗中），其次最新一条（与 person_profile._current_arrangement 同款）
    current_by_person = {}
    for pid, arrs in by_person.items():
        current_by_person[pid] = next((a for a in arrs if a.stage == 'ONGOING'), arrs[0])

    # 一次取回这些安排下的全部轮岗期评分（按 arrangement 归组）
    scores_by_arr = {}
    arr_ids = [a.id for a in arrangements]
    if arr_ids:
        rows = (
            RotationStage.objects
            .filter(arrangement_id__in=arr_ids, deleted_at__isnull=True)
            .values_list('arrangement_id', 'score')
        )
        for arr_id, score in rows:
            if score is None:
                continue
            scores_by_arr.setdefault(arr_id, []).append(float(score))

    for p in persons:
        entry = result[str(p.id)]
        arrs = by_person.get(p.id) or []
        current = current_by_person.get(p.id)
        if current is not None:
            entry['rotation_status'] = current.stage or ''
            entry['rotation_status_label'] = STAGE_LABELS.get(current.stage, current.stage or '')
            dept = current.current_dept.name if current.current_dept_id else ''
            entry['rotation_dept'] = dept or (p.bu or '')
        all_scores = []
        for a in arrs:
            all_scores.extend(scores_by_arr.get(a.id, []))
        entry['overall_score'] = _avg(all_scores)
    return result
