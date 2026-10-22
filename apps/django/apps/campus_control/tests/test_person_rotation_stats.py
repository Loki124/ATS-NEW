"""人员列表的轮岗维度指标（2026-10-22 兵哥指令：列表新增「轮岗状态 / 当前轮岗部门 / 综合评分」+ 轮岗状态筛选）。

锁四件事：
  1. 列表行**下发**这四个字段（rotation_status / rotation_status_label / rotation_dept / overall_score）；
  2. 综合评分 = 轮岗期评分的算术平均（口径同档案详情）；无评分 → None（不臆造 0 分）；
  3. `?rotation_status=` 过滤生效（存在该阶段的轮岗安排）；
  4. 聚合是**批量**的：查询数不随行数线性增长（防 N+1 回归）。

关联口径：`RotationArrangement.person_id == Person.user_id`
（RotationArrangement.person_id 是 BigInteger，语义引用校招生的关联用户 id；Person.id 是 nanoid，不可比较）。
"""
from datetime import date
from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.campus_control.models import Person
from apps.campus_control.person_rotation_stats import build_rotation_stats_map
from apps.campus_rotation.models import RotationArrangement, RotationStage

BASE = '/api/v1/campus'


def _uid():
    import uuid
    return uuid.uuid4().hex[:8].upper()


def _emp_id():
    import random
    return f'{random.randint(10**7, 10**8 - 1):08d}'


def _make_person(user, **kwargs):
    data = dict(
        code=f'C{_uid()}', name='张三', bu='能电BG', school='985', sex='男',
        major='工学', month='1月', status='在职', created_by=user, updated_by=user,
        employee_id=_emp_id(), actual_entry_date=date(2026, 1, 5),
        expected_entry_date=date(2026, 1, 1),
    )
    data.update(kwargs)
    return Person.objects.create(**data)


def _make_arrangement(user, person_user_id, dept=None, stage='ONGOING'):
    return RotationArrangement.objects.create(
        person_id=person_user_id,
        intent_bu='能电BG',
        current_dept=dept,
        stage=stage,
        created_by=user,
        updated_by=user,
    )


def _make_stage(user, arrangement, score, stage_no=1):
    return RotationStage.objects.create(
        arrangement=arrangement,
        stage_no=stage_no,
        assessment_status='DONE',
        score=Decimal(str(score)),
        created_by=user,
        updated_by=user,
    )


def test_person_list_down_throws_rotation_fields(auth_client, super_user):
    """① 列表行下发四个新字段。"""
    _make_person(super_user)
    resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
    assert resp.status_code == 200
    rows = resp.json()['data']
    assert rows
    row = rows[0]
    # 注意：API 响应键由全局渲染器统一转 camelCase
    for key in ('rotationStatus', 'rotationStatusLabel', 'rotationDept', 'overallScore'):
        assert key in row, f'列表行应下发 {key}'
    # 无关联轮岗记录时：状态为空、评分为 None（不臆造 0 分）
    assert row['rotationStatus'] == ''
    assert row['overallScore'] is None


def test_rotation_status_and_score_aggregated(auth_client, super_user, dept_a):
    """② 轮岗状态 / 当前轮岗部门 / 综合评分 按「person_id == user_id」口径聚合。"""
    person = _make_person(super_user, user_id=987654)
    arr = _make_arrangement(super_user, 987654, dept=dept_a, stage='ONGOING')
    _make_stage(super_user, arr, 90, stage_no=1)
    _make_stage(super_user, arr, 80, stage_no=2)

    resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
    assert resp.status_code == 200
    row = next(r for r in resp.json()['data'] if r['id'] == str(person.id))
    assert row['rotationStatus'] == 'ONGOING'
    assert row['rotationStatusLabel'] == '轮岗中'
    assert row['rotationDept'] == dept_a.name
    assert row['overallScore'] == 85.0


def test_overall_score_none_without_scores(auth_client, super_user):
    """无轮岗期评分 → overall_score 为 None（不是 0）。"""
    person = _make_person(super_user, user_id=987655)
    _make_arrangement(super_user, 987655, stage='ONGOING')

    resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
    row = next(r for r in resp.json()['data'] if r['id'] == str(person.id))
    assert row['overallScore'] is None
    assert row['rotationStatus'] == 'ONGOING'


def test_rotation_status_filter(auth_client, super_user):
    """③ ?rotation_status= 过滤生效。"""
    p1 = _make_person(super_user, name='轮岗中的', user_id=987660)
    p2 = _make_person(super_user, name='待分配的', user_id=987661)
    _make_arrangement(super_user, 987660, stage='ONGOING')
    _make_arrangement(super_user, 987661, stage='PENDING')

    resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200, 'rotation_status': 'ONGOING'})
    assert resp.status_code == 200
    ids = {r['id'] for r in resp.json()['data']}
    assert str(p1.id) in ids
    assert str(p2.id) not in ids


def test_rotation_status_filter_ignores_illegal_value(auth_client, super_user):
    """非法 rotation_status 不得报错（按未过滤处理）。"""
    _make_person(super_user, user_id=987662)
    resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200, 'rotation_status': 'NOT_A_STAGE'})
    assert resp.status_code == 200
    assert isinstance(resp.json()['data'], list)


def test_rotation_aggregation_is_batched(auth_client, super_user):
    """④ 聚合是批量的：查询数不随行数线性增长（防 N+1 回归）。"""
    for i in range(12):
        _make_person(super_user, user_id=988000 + i)
        arr = _make_arrangement(super_user, 988000 + i, stage='ONGOING')
        _make_stage(super_user, arr, 80 + i)

    with CaptureQueriesContext(connection) as ctx:
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
        assert resp.status_code == 200
        rows = resp.json()['data']
    assert rows
    # 12 人：批量聚合固定 2 次查询（安排 + 轮岗期），整体查询数远小于「每行 2 次」的 24 次
    assert len(ctx.captured_queries) < 24, f'疑似 N+1：{len(ctx.captured_queries)} 次查询'


def test_build_rotation_stats_map_pure_function(super_user):
    """纯函数：直接调用批量聚合，验证口径与空数据兜底。"""
    person = _make_person(super_user, user_id=988100)
    arr = _make_arrangement(super_user, 988100, stage='DONE')
    _make_stage(super_user, arr, 75.5)

    stats = build_rotation_stats_map([person])
    entry = stats[str(person.id)]
    assert entry['rotation_status'] == 'DONE'
    assert entry['rotation_status_label'] == '已完成'
    assert entry['overall_score'] == 75.5
    # 无轮岗安排 → 当前轮岗部门回退人员自身的 bu
    lonely = _make_person(super_user, name='无轮岗', user_id=988101)
    entry2 = build_rotation_stats_map([lonely])[str(lonely.id)]
    assert entry2['rotation_status'] == ''
    assert entry2['rotation_dept'] == lonely.bu
    assert entry2['overall_score'] is None
