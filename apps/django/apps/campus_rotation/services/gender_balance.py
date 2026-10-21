"""
性别均衡分配算法（需求 5-7）。

设计要点：
- 纯函数、无 Django 依赖，便于单测（禁 mount）。
- 输入为普通 dict 列表（调用方按 DB 组装），输出为「建议」分配，不写库、不强制落库。
- 按 BU 维度分组：同 BU 的校招生只分配到同 BU 的轮岗资源；BU 缺失者归入单一默认组。
- 贪心 + 代价函数：每轮选取「男占比偏离目标最大」的资源，分配其最缺的性别；
  并列时按「剩余容量最大」平手，再并列按资源 id 稳定排序 → 结果可复现。
- 容量为 0 的资源跳过（剩余容量 ≤ 0 永不入选）。
- 当某组输入性别分布本身无法满足目标比例（偏差 > 容忍阈值）→ 标记 imbalanced=True，
  交 BP 手动调整（需求已给兜底：算法作为建议，不强求绝对公平）。

输入契约：
- person: {'id': <hashable>, 'sex': '男'|'女', 'bu': <optional, hashable>}
         sex 非 '男' 一律按女性处理（容错）。
- resource: {'id': <hashable>, 'capacity': int>=0, 'male_count': int>=0,
             'female_count': int>=0, 'bu': <optional, hashable>}
         capacity/male_count/female_count 缺省为 0。

输出契约（dict）：
- 'assignments': [{'person_id', 'resource_id'}, ...]  # 稳定顺序
- 'unassigned': [person_id, ...]
- 'imbalanced': bool
- 'per_resource': {rid: {'male','female','assigned','capacity'}}
- 'by_bu': {bu: {'male','female','deviation'}}
"""

from collections import defaultdict

# 目标男占比（男:女 = 6:4）。函数参数 ratio 可覆盖。
DEFAULT_MALE_RATIO = 0.6
# 单组男占比最大允许偏差；超过则标记 imbalanced。
RATIO_DEVIATION_TOLERANCE = 0.25

MALE = '男'
FEMALE = '女'


def _sex_bucket(sex):
    """将任意性别取值归一到 bool（True=男）。非 '男' 一律视为女（容错）。"""
    return sex == MALE


def _resource_state(resource):
    """归一化资源为内部状态 dict。"""
    rid = resource.get('id')
    capacity = int(resource.get('capacity', 0) or 0)
    male = int(resource.get('male_count', 0) or 0)
    female = int(resource.get('female_count', 0) or 0)
    bu = resource.get('bu', None)
    return {
        'id': rid,
        'bu': bu,
        'capacity': capacity,
        'male': male,   # 既有占用 + 已分配
        'female': female,
        'assigned': 0,
    }


def _group_by_bu(persons, resources):
    """按 BU 分组；缺失 BU 的资源/人员归入 None 组，仍参与分配。"""
    groups = defaultdict(lambda: {'resources': [], 'persons': []})
    for r in resources:
        st = _resource_state(r)
        groups[st['bu']]['resources'].append(st)
    for p in persons:
        bu = p.get('bu', None)
        groups[bu]['persons'].append(p)
    return groups


def _select_resource(states, male_ratio):
    """
    选取本轮要接收人员的资源：男占比偏离目标最大者优先；
    并列按剩余容量最大，再并列按资源 id 稳定排序。
    剩余容量 ≤ 0 的资源不可选（跳过）。
    """
    candidates = [s for s in states if (s['capacity'] - s['male'] - s['female']) > 0]
    if not candidates:
        return None
    def deviation(s):
        total = s['male'] + s['female']
        if total == 0:
            return abs(0.0 - male_ratio)  # 空资源，偏差=目标本身（最大）
        return abs((s['male'] / total) - male_ratio)
    def remaining(s):
        return s['capacity'] - s['male'] - s['female']
    # 偏差降序（最不平衡优先）、剩余容量降序、id 升序 → 稳定
    candidates.sort(key=lambda s: (-deviation(s), -remaining(s), s['id']))
    return candidates[0]


def _needed_gender(state, male_ratio):
    """给定资源当前占用，下一人的目标性别：让男占比更接近目标。"""
    total_after = state['male'] + state['female'] + 1
    target_male = round(male_ratio * total_after)
    if state['male'] < target_male:
        return MALE
    return FEMALE


def allocate_by_gender(persons, resources, ratio=DEFAULT_MALE_RATIO):
    """
    按性别比例分配校招生到轮岗资源（建议，不落库）。

    :param persons: list[dict]，契约见模块头。
    :param resources: list[dict]，契约见模块头。
    :param ratio: 目标男占比（默认 0.6）。
    :return: dict（契约见模块头）。
    """
    if ratio is None or ratio < 0 or ratio > 1:
        ratio = DEFAULT_MALE_RATIO

    groups = _group_by_bu(persons, resources)
    assignments = []
    unassigned = []
    per_resource = {}
    by_bu = {}

    for bu, grp in groups.items():
        states = sorted(grp['resources'], key=lambda s: s['id'])  # 稳定起点
        # 待分配人员按 id 排序，保证可复现
        pending = sorted(grp['persons'], key=lambda p: p.get('id'))

        while pending:
            target = _select_resource(states, ratio)
            if target is None:
                # 该组资源已满或不存在 → 剩余人员无法分配
                unassigned.extend(p.get('id') for p in pending)
                break
            need = _needed_gender(target, ratio)
            # 优先取所需性别；没有则退而取另一性别（尽力而为）
            chosen_idx = None
            for i, p in enumerate(pending):
                if _sex_bucket(p.get('sex')) == (need == MALE):
                    chosen_idx = i
                    break
            if chosen_idx is None:
                chosen_idx = 0
            person = pending.pop(chosen_idx)
            is_male = _sex_bucket(person.get('sex'))
            if is_male:
                target['male'] += 1
            else:
                target['female'] += 1
            target['assigned'] += 1
            assignments.append({'person_id': person.get('id'), 'resource_id': target['id']})

        # 汇总该组
        grp_male = sum(s['male'] for s in states)
        grp_female = sum(s['female'] for s in states)
        grp_dev = 0.0
        for s in states:
            total = s['male'] + s['female']
            if total > 0:
                grp_dev = max(grp_dev, abs((s['male'] / total) - ratio))
            else:
                grp_dev = max(grp_dev, ratio)
        by_bu[bu] = {'male': grp_male, 'female': grp_female, 'deviation': grp_dev}
        for s in states:
            per_resource[s['id']] = {
                'male': s['male'],
                'female': s['female'],
                'assigned': s['assigned'],
                'capacity': s['capacity'],
            }

    imbalanced = any(b['deviation'] > RATIO_DEVIATION_TOLERANCE for b in by_bu.values())
    # 人员/资源 id 已排序，assignments 顺序天然稳定；再显式排序兜底
    assignments.sort(key=lambda a: (a['resource_id'], a['person_id']))
    unassigned.sort(key=lambda x: (str(type(x)), x) if not isinstance(x, (int, str)) else x)

    return {
        'assignments': assignments,
        'unassigned': unassigned,
        'imbalanced': imbalanced,
        'per_resource': per_resource,
        'by_bu': by_bu,
    }
