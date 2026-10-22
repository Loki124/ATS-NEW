"""
轮岗资源 · 「统计概览」聚合（纯函数，无 Django 依赖，便于单测）。

## 行粒度

**BG × 当前BU**。组织维度的取值域来自**校招生档案**（与需求方原表同源）：

- BG     = `Person.bu`（BG 名，如「能电BG」）
- 当前BU = `Person.intent_bu`（投递意向 BU；为空 → 「未分配」）

⚠️ 为什么不拿 Department 树当行粒度：部门树与 `Person.bu` 是**两套命名空间**
（部门树里是「能良 / 醒市 / 技术中心」这类事业群名，档案里是「能电BG / 三到BG」这类 BG 名），
两者按名字 join 不上 → 强行 join 会让整表归零。故以档案侧为准，部门侧只用于需求归集。

## 逐列口径

| 列 | 口径 | 输入来源 |
|---|---|---|
| BG 单元格的人数 | 该 BG 下校招生总人数（不限状态） | `Person` |
| 业务需求 | 校招需求人数合计（按 BU 名归集） | `Demand`（recruit_type=campus） |
| 已定岗 | 轮岗安排中已填「定岗去向」的人数 | `RotationArrangement.final_dept` 非空 |
| 定岗流失 | 已定岗、且当前已离职的人数 | 同上 + 人员状态=离职 |
| 满足率 | 已定岗 / 业务需求（分母 0 → null） | 计算 |
| 入职 | 有实际入职日期的人数 | `Person.actual_entry_date` |
| 离职 | 状态=离职 的人数 | `Person.status` |
| 在职 | 状态=在职 的人数 | `Person.status` |
| 留存率 | 在职 / 入职（分母 0 → null） | 计算 |
| 离职分布 客服/主播/其他岗位 | 离职人员按**轮岗资源类型**分布 | `RotationArrangement.resource.resource_type` |
| 在职分布 客服/主播/其他岗位 | 在职人员按**轮岗资源类型**分布 | 同上 |
| 性别分布(当前) 男/女 | **在职**校招生的性别分布 | `Person.sex` |
| 意向BU 男/女 | 该 BU **投递意向人群**（不限状态）的性别分布 | `Person.sex` |
| 女生比 | 意向女 /（意向男 + 意向女）（分母 0 → null） | 计算 |

**比率一律「分母为 0 → null」**：不静默当成 0（0 是「确实为零」，null 是「分母为零、无意义」，
两者在看板上必须可区分）。

## 输入契约

persons: list[dict]
    - `bg`      str  BG 名（空 → 未分配 BG）
    - `bu`      str  当前BU 名（空 → 未分配）
    - `sex`     str  '男' / '女'（其它值按未知处理，不计入男/女）
    - `status`  str  '在职' / '待入职' / '离职'
    - `onboarded` bool 是否已入职（有实际入职日期）

arrangements: list[dict]
    - `bg` / `bu`       str  同 persons
    - `resource_type`   str  'LIVE_ROOM'（主播）/ 'SERVICE_DEPT'（客服）/ 'OTHER'（其他岗位）
    - `person_status`   str  关联人员的状态
    - `fixed`           bool  是否已定岗（定岗去向非空）

demands: list[dict]
    - `bu`        str  需求所属 BU 名（部门树口径）
    - `bg`        str  需求所属 BG 名（部门树口径）
    - `headcount` int  需求人数

    归集规则：先按 `bu` 名匹配行 → 再按 `bg` 名匹配行 → 都不匹配则落到
    「未分配 BG / 未分配」行（**需求不丢弃**，同时计入 `unassignedDemand` 供前端提示核对）。

## 输出契约

- `rows`   list[dict]  逐行明细（首行是「整体」汇总行）
- `totals` dict        与首行同构的汇总值（前端顶部概览条直接用）
- `unassignedDemand` int  未能归属到任何 BU 的需求人数（前端提示核对，不静默丢弃）

行内额外字段 `bgSpan`：BG 跨行合并行数（组首行 = 组内行数，其余行 = 0），
由本模块计算，前端直接喂给 naive-ui 的 `rowSpan`。
"""
from collections import defaultdict

# 组织维度缺省值（与前端展示文案一致）
UNASSIGNED_BG = '未分配 BG'
UNASSIGNED_BU = '未分配'

# 轮岗资源类型 → (离职分布列, 在职分布列)
# 与需求方原表的「客服 / 主播 / 其他岗位」对应。
RESOURCE_TYPE_TO_COLUMNS = {
    'SERVICE_DEPT': ('offCS', 'onCS'),        # 客服
    'LIVE_ROOM': ('offAnchor', 'onAnchor'),  # 主播
    'OTHER': ('offOther', 'onOther'),         # 其他岗位
}

STATUS_ACTIVE = '在职'
STATUS_LEFT = '离职'
SEX_MALE = '男'
SEX_FEMALE = '女'

# 「整体」汇总行的组织名
OVERALL_BG = '整体'
OVERALL_BU = '整体'

# BG 小计行的「当前BU」列取值（与需求方原表的「BG汇总」行同名，前端统一弱化样式）
SUBTOTAL_BU_NAME = 'BG汇总'


def _rate(numerator: float, denominator: float):
    """比率：分母为 0 → None（不静默当成 0）。"""
    if not denominator:
        return None
    return numerator / denominator


def _empty_cell() -> dict:
    """一行（BG × BU）的初始指标累加器。"""
    return {
        'demand': 0, 'fixed': 0, 'lost': 0,
        'onboard': 0, 'offboard': 0, 'active': 0,
        'offCS': 0, 'offAnchor': 0, 'offOther': 0,
        'onCS': 0, 'onAnchor': 0, 'onOther': 0,
        'male': 0, 'female': 0,
        'intendMale': 0, 'intendFemale': 0,
    }


def _finalize(cell: dict) -> dict:
    """补上派生比率（满足率 / 留存率 / 女生比）。"""
    out = dict(cell)
    out['fillRate'] = _rate(cell['fixed'], cell['demand'])
    out['retainRate'] = _rate(cell['active'], cell['onboard'])
    intent_total = cell['intendMale'] + cell['intendFemale']
    out['femaleRatio'] = _rate(cell['intendFemale'], intent_total)
    return out


def build_stats_overview(*, persons, arrangements, demands) -> dict:
    """聚合统计概览数据。

    :param persons: list[dict]，契约见模块头。
    :param arrangements: list[dict]，契约见模块头。
    :param demands: list[dict]，契约见模块头。
    :return: dict —— {'rows': [...], 'totals': {...}, 'unassignedDemand': int}，契约见模块头。
    """
    persons = persons or []
    arrangements = arrangements or []
    demands = demands or []

    # 键：(BG, 当前BU) → 累加器
    cells: dict = defaultdict(_empty_cell)
    # BG → 该 BG 下校招生总人数（不限状态；BG 单元格右侧的人数）
    bg_total: dict = defaultdict(int)

    # ── 人员侧：入职/离职/在职 + 性别分布(在职) + 意向BU 男女(全体) ──
    for p in persons:
        bg = p.get('bg') or UNASSIGNED_BG
        bu = p.get('bu') or UNASSIGNED_BU
        key = (bg, bu)
        cell = cells[key]
        status = p.get('status') or ''
        sex = p.get('sex') or ''

        bg_total[bg] += 1
        if p.get('onboarded'):
            cell['onboard'] += 1
        if status == STATUS_LEFT:
            cell['offboard'] += 1
        if status == STATUS_ACTIVE:
            cell['active'] += 1
            # 性别分布(当前)：在职口径
            if sex == SEX_MALE:
                cell['male'] += 1
            elif sex == SEX_FEMALE:
                cell['female'] += 1
        # 意向BU：投递意向人群（不限状态）
        if sex == SEX_MALE:
            cell['intendMale'] += 1
        elif sex == SEX_FEMALE:
            cell['intendFemale'] += 1

    # ── 需求侧：业务需求按 BU 名 / BG 名归集 ──
    # ⚠️ 部门的 BU 名与档案侧 BU 名可能不同源（见模块头说明）：
    #    对不上号的 BU **不丢弃**，落到「未分配 BG / 未分配」行，
    #    同时计入 `unassignedDemand` 供前端提示核对。
    #    一个 BU 名理论上只属于一个 BG；若出现同名多行（脏数据），
    #    只归给第一行 —— **绝不按行数摊派**（会造出假数）。
    bu_index: dict = defaultdict(list)
    bg_index: dict = defaultdict(list)
    for key in cells:
        bu_index[key[1]].append(key)
        bg_index[key[0]].append(key)
    unassigned_demand = 0
    for d in demands:
        headcount = int(d.get('headcount') or 0)
        if not headcount:
            continue
        bu_key = d.get('bu') or ''
        bg_key = d.get('bg') or ''
        target = None
        if bu_key and bu_index.get(bu_key):
            target = sorted(bu_index[bu_key])[0]
        elif bg_key and bg_index.get(bg_key):
            target = sorted(bg_index[bg_key])[0]
        if target is None:
            target = (UNASSIGNED_BG, UNASSIGNED_BU)
            unassigned_demand += headcount
        cells[target]['demand'] += headcount

    # ── 轮岗安排侧：已定岗 / 定岗流失 / 离职与在职的资源类型分布 ──
    for a in arrangements:
        bg = a.get('bg') or UNASSIGNED_BG
        bu = a.get('bu') or UNASSIGNED_BU
        # 该 BU 在人员侧不存在时也要留一行（否则有轮岗安排却查无此行）
        cell = cells[(bg, bu)]
        if a.get('fixed'):
            cell['fixed'] += 1
            if a.get('person_status') == STATUS_LEFT:
                cell['lost'] += 1
        cols = RESOURCE_TYPE_TO_COLUMNS.get(a.get('resource_type') or '')
        if cols:
            off_col, on_col = cols
            status = a.get('person_status') or ''
            if status == STATUS_LEFT:
                cell[off_col] += 1
            elif status == STATUS_ACTIVE:
                cell[on_col] += 1

    # ── 组装行：整体行 + 各 BG 分组行 ──
    overall = _empty_cell()
    for cell in cells.values():
        for k, v in cell.items():
            overall[k] += v

    by_bg: dict = defaultdict(list)
    for (bg, bu), cell in cells.items():
        by_bg[bg].append((bu, cell))

    # BG 排序：人数多的在前；人数相同按名字稳定排序
    bg_order = sorted(by_bg.keys(), key=lambda bg: (-bg_total.get(bg, 0), bg))
    rows: list = []
    for bg in bg_order:
        items = sorted(by_bg[bg], key=lambda it: (-it[1]['active'], it[0]))
        # BG 合并格覆盖组内全部行（含末尾的 BG 小计行），与需求方原表一致
        span = len(items) + 1
        group_cells = _empty_cell()
        for idx, (bu, cell) in enumerate(items):
            for k, v in cell.items():
                group_cells[k] += v
            row = _finalize(cell)
            row['bgGroup'] = bg
            row['bgTotal'] = bg_total.get(bg, 0)
            row['buName'] = bu
            # 组首行承载跨行合并的行数，其余行 0（naive-ui rowSpan 语义）
            row['bgSpan'] = span if idx == 0 else 0
            rows.append(row)
        # BG 小计行（组末）：与需求方原表的「BG汇总」行同名同位，前端统一弱化样式
        subtotal = _finalize(group_cells)
        subtotal['bgGroup'] = bg
        subtotal['bgTotal'] = bg_total.get(bg, 0)
        subtotal['buName'] = SUBTOTAL_BU_NAME
        subtotal['bgSpan'] = 0
        rows.append(subtotal)

    total_row = _finalize(overall)
    total_row['bgGroup'] = OVERALL_BG
    total_row['bgTotal'] = None
    total_row['buName'] = OVERALL_BU
    total_row['bgSpan'] = 0

    return {
        'rows': [total_row] + rows,
        'totals': total_row,
        'unassignedDemand': unassigned_demand,
    }
