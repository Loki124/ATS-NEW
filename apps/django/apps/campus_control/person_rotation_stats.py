"""人员列表的轮岗维度批量聚合（2026-10-22 兵哥指令：列表新增「轮岗状态 / 当前轮岗部门 / 综合评分」）。

## 为什么要单独抽模块

列表要按页下发多个轮岗维度指标，若在序列化器里逐行查轮岗安排 + 轮岗期考核，
200 行就是 400 次查询（N+1）。本模块按**整页人员一次性批量聚合**，
结果经 ViewSet 的 serializer context 交给序列化器渲染。

## 口径（与个人档案详情 `person_profile.py` **完全一致**，避免列表与详情对不上）

- 关联：**优先 `RotationArrangement.campus_person == Person.id`**（人员级 nanoid 口径，
  2026-10-22 新增）；旧数据回退 `RotationArrangement.person_id == Person.user_id`
  （BigInteger 账号 id 口径；dev 库里校招生基本没有账号 → 该口径查不到任何安排）。
- 当前轮岗安排：优先 `ONGOING`（轮岗中），其次按创建时间倒序取最新一条。
- 轮岗状态：当前安排的 `stage`（同时给出 code 与中文标签）。
- 当前轮岗部门（2026-10-23 聂荣口径调整）：
  **「基于轮岗的直播间取所在 BU 部门」** —— 取当前安排所挂轮岗资源的 `resource.bu.name`
  （轮岗资源 = 直播间 / 客服部门 / 其他三形态合一表，`resource.bu` = 归属 BU）。
  回退链：`resource.bu.name` → `current_dept.name` → `Person.bu`。
  ⚠️ 不按 resource_type 特判「只有直播间才算」：客服部门形态同样有归属 BU，
    特判会让非直播间形态的「当前轮岗部门」恒空，反而与业务口径不符。
- HRBP 建议值（2026-10-23 聂荣口径「HRBP 基于轮岗 BU 部门的 HRBP 自动填充」）：
  取该 BU 部门的 `Department.hrbp`（`core/models.py` 的「部门HRBP」字段）。
  仅作**自动填充的建议值**下发，已被人工指定过的 `Person.hrbp` 优先。
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
        'rotation_bu_name': '',
        'suggested_hrbp_id': '',
        'overall_score': None,
    }


def _collect_arrangements(persons):
    """一次取回本页人员关联的全部轮岗安排，按 Person 主键归组。

    :return: ({person_id: [arrangement, ...]}, [arrangement, ...])
    """
    user_ids = [p.user_id for p in persons if p.user_id]
    person_ids = [p.id for p in persons]

    arrangements = list(
        RotationArrangement.objects.filter(
            Q(campus_person_id__in=person_ids) | Q(person_id__in=user_ids),
            deleted_at__isnull=True,
        ).select_related(
            'current_dept', 'campus_person', 'resource', 'resource__bu',
        ).order_by('-created_at')
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
    return by_person, arrangements


def build_rotation_stats_map(persons):
    """批量聚合一页人员的轮岗维度指标。

    :param persons: Person 实例序列（通常是当前分页页内的对象）
    :return: {person_id(str): {'rotation_status', 'rotation_status_label',
                                'rotation_dept', 'rotation_bu_name',
                                'suggested_hrbp_id', 'overall_score'}}
    """
    persons = list(persons)
    if not persons:
        return {}

    result = {str(p.id): _empty_entry(p) for p in persons}
    by_person, arrangements = _collect_arrangements(persons)

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
            # 当前轮岗部门：轮岗资源所在 BU 优先（聂荣 2026-10-23 口径）
            bu = current.resource.bu if current.resource_id else None
            dept_name = bu.name if bu is not None else ''
            fallback_dept = current.current_dept.name if current.current_dept_id else ''
            entry['rotation_dept'] = dept_name or fallback_dept or (p.bu or '')
            entry['rotation_bu_name'] = dept_name
            if bu is not None and bu.hrbp_id:
                entry['suggested_hrbp_id'] = str(bu.hrbp_id)
        all_scores = []
        for a in arrs:
            all_scores.extend(scores_by_arr.get(a.id, []))
        entry['overall_score'] = _avg(all_scores)
    return result


def suggested_hrbp_id_for_person(person):
    """该生当前轮岗 BU 部门的 HRBP id（无轮岗安排 / BU 未配 HRBP 时返回 ''）。

    用于**写入时自动填充** `Person.hrbp`（聂荣 2026-10-23 口径：
    「HRBP（基于轮岗BU部门的HRBP自动填充，可修改）」）。
    单人写入路径，1 次查询可接受。
    """
    if person is None:
        return ''
    arrangements = list(
        RotationArrangement.objects.filter(
            Q(campus_person_id=person.id)
            | (Q(person_id=person.user_id) if person.user_id else Q(pk__in=[])),
            deleted_at__isnull=True,
        ).select_related('resource', 'resource__bu').order_by('-created_at')
    )
    if not arrangements:
        return ''
    current = next((a for a in arrangements if a.stage == 'ONGOING'), arrangements[0])
    bu = current.resource.bu if current.resource_id else None
    if bu is None or not bu.hrbp_id:
        return ''
    return str(bu.hrbp_id)
