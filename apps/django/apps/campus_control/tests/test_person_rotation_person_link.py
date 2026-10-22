"""人员级关联口径（2026-10-22）：按「校招生档案」定位轮岗安排。

## 为什么要有这个文件

轮岗安排原先只用 `RotationArrangement.person_id`（BigInteger，语义 = `Person.user_id`
账号 id）。但校招生**普遍没有账号**（测试库/dev 库里 56 名校招生 user_id 全为空），
于是「按轮岗状态筛人」在真实数据上一条都筛不出来 —— 这是静默失效，不是「没数据」。

2026-10-22 新增 `RotationArrangement.campus_person`（Person 主键 nanoid）作为
人员级关联，并把 `person_id` 退化为派生镜像字段。本文件锁三件事：

1. `?rotation_status=` 筛选按 **campus_person 口径**生效（新口径）；
2. 旧口径（`person_id` ↔ `Person.user_id`）**仍然可用** —— 历史数据不能因新口径而失效；
3. 档案详情（`person_profile`）与列表口径**一致** —— 列表能看到的轮岗，详情也看得到。

## 数据纪律

这些用例**必须自建数据**，不能依赖种子库：
种子/真实库里校招生的 `user_id` 全为空，走旧口径根本命中不了，
用「碰巧命中」写断言会得到假绿。

⚠️ `RotationArrangement.person_id` 已改为可空（校招生无账号时为 NULL），
   所以旧口径的用例必须显式给出 `user_id`，否则筛不出来。
"""
import random
import uuid
from datetime import date

import pytest

from apps.campus_control.models import Person
from apps.campus_rotation.models import RotationArrangement

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus'


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _emp_id():
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


def _make_arrangement(user, *, campus_person=None, person_id=None, stage='ONGOING'):
    return RotationArrangement.objects.create(
        campus_person=campus_person,
        person_id=person_id,
        intent_bu='能电BG',
        stage=stage,
        created_by=user,
        updated_by=user,
    )


def test_rotation_status_filter_matches_campus_person_link(auth_client, super_user):
    """① 新口径：`campus_person` 关联的安排能筛出该人；无关的人筛不到。"""
    linked = _make_person(super_user, name='人员级关联')
    unrelated = _make_person(super_user, name='无轮岗安排')
    _make_arrangement(super_user, campus_person=linked, stage='ONGOING')

    resp = auth_client.get(
        f'{BASE}/persons/', {'page_size': 200, 'rotation_status': 'ONGOING'},
    )
    assert resp.status_code == 200
    ids = {r['id'] for r in resp.json()['data']}
    assert str(linked.id) in ids
    assert str(unrelated.id) not in ids


def test_rotation_status_filter_still_matches_legacy_user_id_link(auth_client, super_user):
    """② 旧口径回退：`person_id` ↔ `Person.user_id` 的历史安排仍然筛得出来。"""
    legacy = _make_person(super_user, name='旧口径关联', user_id=987701)
    _make_arrangement(super_user, person_id=987701, stage='PENDING')

    resp = auth_client.get(
        f'{BASE}/persons/', {'page_size': 200, 'rotation_status': 'PENDING'},
    )
    assert resp.status_code == 200
    ids = {r['id'] for r in resp.json()['data']}
    assert str(legacy.id) in ids


def test_person_profile_uses_campus_person_link(auth_client, super_user):
    """③ 档案详情与列表同口径：`campus_person` 关联的轮岗在详情里可见。

    反例（修之前）：详情只认 `person_id == Person.user_id`，而校招生无账号 →
    详情轮岗区段恒为空，与列表列显示的轮岗状态对不上。
    """
    person = _make_person(super_user, name='详情口径一致')
    _make_arrangement(super_user, campus_person=person, stage='ONGOING')

    resp = auth_client.get(f'{BASE}/persons/{person.id}/profile/')
    assert resp.status_code == 200, resp.content
    data = resp.json()['data']
    assert data['rotation'] is not None, '档案详情应能看到人员级关联的轮岗安排'
    assert data['rotation']['stage'] == 'ONGOING'


def test_person_profile_without_user_id_is_not_empty(auth_client, super_user):
    """④ 无账号的校招生也能按人员级关联查到轮岗（旧实现直接短路返回空）。"""
    person = _make_person(super_user, name='无账号')
    assert person.user_id is None
    _make_arrangement(super_user, campus_person=person, stage='ONGOING')

    resp = auth_client.get(f'{BASE}/persons/{person.id}/profile/')
    assert resp.status_code == 200, resp.content
    assert resp.json()['data']['rotation'] is not None
