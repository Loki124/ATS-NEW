"""
性别均衡分配算法纯函数单测（需求 5-7，S5-20）。

纪律：纯函数不 mount、不依赖 DB（pytest 不加 django_db 标记）。
覆盖规格要求的四类：
  1. 男女各 10 人分 2 资源 → 偏差 ≤ tolerance（不失衡）
  2. 单一性别输入（全男）→ 不崩溃，imbalanced=True
  3. 容量为 0 的资源被跳过
  4. 同一输入两次调用结果一致（可复现性）
另加：资源容量不足 → 多余人员进入 unassigned。
"""

from apps.campus_rotation.services.gender_balance import (
    allocate_by_gender,
    DEFAULT_MALE_RATIO,
    RATIO_DEVIATION_TOLERANCE,
    MALE,
    FEMALE,
)


def _make_persons(ids_sex):
    """ids_sex: list of (id, sex)。"""
    return [{'id': pid, 'sex': sex} for pid, sex in ids_sex]


def _make_resources(specs):
    """specs: list of (id, capacity)。默认 male_count/female_count=0、bu=None。"""
    return [{'id': rid, 'capacity': cap, 'male_count': 0, 'female_count': 0} for rid, cap in specs]


def test_balanced_split_deviation_within_tolerance():
    persons = _make_persons(
        [(f'P{i}', MALE) for i in range(10)]
        + [(f'Q{i}', FEMALE) for i in range(10)]
    )
    resources = _make_resources([('R1', 20), ('R2', 20)])
    result = allocate_by_gender(persons, resources)

    assert result['imbalanced'] is False
    assert len(result['assignments']) == 20
    assert result['unassigned'] == []

    total_male = sum(r['male'] for r in result['per_resource'].values())
    total_female = sum(r['female'] for r in result['per_resource'].values())
    assert total_male == 10
    assert total_female == 10

    for rid, st in result['per_resource'].items():
        total = st['male'] + st['female']
        assert total == 10  # 两资源各 10 人
        dev = abs((st['male'] / total) - DEFAULT_MALE_RATIO)
        assert dev <= RATIO_DEVIATION_TOLERANCE


def test_all_male_input_marks_imbalanced_no_crash():
    persons = _make_persons([(f'P{i}', MALE) for i in range(10)])
    resources = _make_resources([('R1', 20), ('R2', 20)])
    result = allocate_by_gender(persons, resources)

    # 全男 → 永远达不到 0.6 男占比目标附近的平衡，应标记失衡且不崩溃
    assert result['imbalanced'] is True
    assert len(result['assignments']) == 10
    total_male = sum(r['male'] for r in result['per_resource'].values())
    assert total_male == 10


def test_zero_capacity_resource_skipped():
    persons = _make_persons([(f'P{i}', MALE) for i in range(5)])
    # R0 容量 0（应被跳过），R1 容量 10
    resources = _make_resources([('R0', 0), ('R1', 10)])
    result = allocate_by_gender(persons, resources)

    assert result['per_resource']['R0']['assigned'] == 0
    assert result['per_resource']['R0']['capacity'] == 0
    assert result['per_resource']['R1']['assigned'] == 5
    assert len(result['assignments']) == 5
    assert result['unassigned'] == []


def test_reproducible_same_input_same_output():
    persons = _make_persons(
        [(f'P{i}', MALE) for i in range(8)]
        + [(f'Q{i}', FEMALE) for i in range(12)]
        + [(f'X{i}', MALE) for i in range(3)]
    )
    resources = _make_resources([('R1', 15), ('R2', 15), ('R3', 10)])
    first = allocate_by_gender(persons, resources)
    second = allocate_by_gender(persons, resources)

    assert first['assignments'] == second['assignments']
    assert first['per_resource'] == second['per_resource']
    assert first['by_bu'] == second['by_bu']
    assert first['imbalanced'] == second['imbalanced']


def test_over_capacity_goes_unassigned():
    # 3 人，但两个资源合计容量只有 2 → 1 人无法分配
    persons = _make_persons([(f'P{i}', MALE) for i in range(3)])
    resources = _make_resources([('R1', 1), ('R2', 1)])
    result = allocate_by_gender(persons, resources)

    assert len(result['assignments']) == 2
    assert result['unassigned'] == ['P2']
    assert result['per_resource']['R1']['assigned'] == 1
    assert result['per_resource']['R2']['assigned'] == 1
