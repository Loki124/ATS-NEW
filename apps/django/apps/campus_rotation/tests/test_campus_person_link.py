"""轮岗安排「校招生档案」人员级关联（2026-10-22）。

## 背景与被修的 bug

轮岗安排表单的「校招生」下拉，其 option value 是 **Person 主键 nanoid**（字符串），
而表单提交时写的是 `personId: Number(formState.person)` → `Number('V1St...')` = **NaN**
→ 后端 400「校招生必须是整数」。且即便数字对了，`person_id` 的语义也是
「校招生**账号 id**」，而校招生普遍没有账号 → 定位不到人。

修法：表单改传 `campusPerson`（Person 主键 nanoid），后端据此建立人员级关联，
并把旧口径 `person_id` 镜像成该人的 `user_id`（无账号 → NULL，`person_id` 已改可空）。

## 本文件锁的五件事

1. POST 传 `campus_person` → 落库正确，`person_id` 被镜像；
2. POST 不给校招生 → 400（中文提示，不静默建出无人的安排）；
3. PUT 不带 `campus_person` → **不清空**已有人员级关联（历史行不被冲掉）；
4. PUT 换人 → 人员级关联与 `person_id` 镜像同步更新；
5. 列表 `?campus_person=` 过滤生效。
"""
import random
import uuid
from datetime import date

import pytest

from apps.campus_control.models import Person
from apps.campus_rotation.models import RotationArrangement

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-rotation'


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _emp_id():
    return f'{random.randint(10**7, 10**8 - 1):08d}'


def _make_person(**kwargs):
    data = dict(
        code=f'C{_uid()}', name='张三', bu='能电BG', school='985', sex='男',
        major='工学', month='1月', status='在职',
        employee_id=_emp_id(), actual_entry_date=date(2026, 1, 5),
        expected_entry_date=date(2026, 1, 1),
    )
    data.update(kwargs)
    return Person.objects.create(**data)


def test_create_with_campus_person_links_archive(auth_client):
    """① 传 campus_person → 人员级关联落库；person_id 镜像为该人的账号 id。"""
    person = _make_person(name='甲', user_id=778001)
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {'campusPerson': str(person.id)},
        format='json',
    )
    assert resp.status_code in (200, 201), resp.content
    arr = RotationArrangement.objects.get(id=resp.json()['data']['id'])
    assert arr.campus_person_id == person.id
    assert arr.person_id == 778001


def test_create_without_account_mirrors_person_id_to_null(auth_client):
    """② 校招生没有账号 → person_id 为 NULL（不是 0、也不是被拒）。"""
    person = _make_person(name='乙')
    assert person.user_id is None
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {'campusPerson': str(person.id)},
        format='json',
    )
    assert resp.status_code in (200, 201), resp.content
    arr = RotationArrangement.objects.get(id=resp.json()['data']['id'])
    assert arr.campus_person_id == person.id
    assert arr.person_id is None


def test_create_without_person_is_rejected(auth_client):
    """③ 不给校招生 → 400 中文提示（person_id 已可空，必须靠应用层守住必填）。"""
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/', {}, format='json',
    )
    assert resp.status_code == 400, resp.content
    assert 'campusPerson' in resp.content.decode()


def test_update_without_campus_person_keeps_link(auth_client):
    """④ PUT 不带 campus_person → 不清空已有人员级关联（历史行不被冲成孤儿）。"""
    person = _make_person(name='丙')
    arr = RotationArrangement.objects.create(
        campus_person=person, intent_bu='能电BG', note='原备注',
    )
    resp = auth_client.put(
        f'{BASE}/rotation-arrangements/{arr.id}/',
        {'note': '只改备注'},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    arr.refresh_from_db()
    assert arr.campus_person_id == person.id
    assert arr.note == '只改备注'


def test_update_with_other_person_relinks(auth_client):
    """⑤ PUT 换人 → 人员级关联与 person_id 镜像同步更新。"""
    old_person = _make_person(name='丁')
    new_person = _make_person(name='戊', user_id=778002)
    arr = RotationArrangement.objects.create(campus_person=old_person, intent_bu='能电BG')

    resp = auth_client.put(
        f'{BASE}/rotation-arrangements/{arr.id}/',
        {'campusPerson': str(new_person.id)},
        format='json',
    )
    assert resp.status_code == 200, resp.content
    arr.refresh_from_db()
    assert arr.campus_person_id == new_person.id
    assert arr.person_id == 778002


def test_list_filter_by_campus_person(auth_client):
    """⑥ 列表按人员级关联过滤。"""
    wanted = _make_person(name='己')
    other = _make_person(name='庚')
    RotationArrangement.objects.create(campus_person=wanted, intent_bu='能电BG')
    RotationArrangement.objects.create(campus_person=other, intent_bu='能电BG')

    resp = auth_client.get(
        f'{BASE}/rotation-arrangements/', {'campus_person': str(wanted.id)},
    )
    assert resp.status_code == 200, resp.content
    rows = resp.json()['data']
    assert rows, '应至少返回一条'
    # 响应经全局 camel-case 渲染 → campus_person 出参为 campusPerson
    assert {str(r['campusPerson']) for r in rows} == {str(wanted.id)}
