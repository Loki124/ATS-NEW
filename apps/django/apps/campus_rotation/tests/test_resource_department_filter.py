"""轮岗资源列表 · 部门**多选**筛选（2026-10-22）

背景：部门树筛选组件（`components/common/DeptTreeFilter.vue`）是**多选**的，
「自动选中全部子部门」开启时回传的是「父部门 + 其全部下级」的 id 列表，
所以后端 `?department=` 必须能接住**逗号分隔的多个部门 id**。

本文件锁：
  1. 单个部门 id → 行为不变（向后兼容，既有调用方不受影响）；
  2. 逗号分隔多部门 → 命中其中任一部门即返回；
  3. 空值 / 空段 / 不存在的 id → 不报错、不误伤（不过滤或返回空，按语义区分）。
"""
import pytest

from apps.campus_rotation.models import RotationResource
from apps.core.models import Department

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-rotation'


@pytest.fixture
def depts(db):
    root = Department.objects.create(id='df-root', name='集团', code='DF_ROOT', path='/集团')
    a = Department.objects.create(id='df-a', name='能电BG', code='DF_A', parent=root, path='/集团/能电BG')
    b = Department.objects.create(id='df-b', name='能战BG', code='DF_B', parent=root, path='/集团/能战BG')
    c = Department.objects.create(id='df-c', name='醒市', code='DF_C', parent=root, path='/集团/醒市')
    return {'root': root, 'a': a, 'b': b, 'c': c}


@pytest.fixture
def resources(db, depts):
    RotationResource.objects.create(name='直播间A', resource_type='LIVE_ROOM', department=depts['a'])
    RotationResource.objects.create(name='直播间B', resource_type='LIVE_ROOM', department=depts['b'])
    RotationResource.objects.create(name='直播间C', resource_type='LIVE_ROOM', department=depts['c'])
    return depts


def _names(resp):
    return {r['name'] for r in resp.json()['data']}


def test_single_department_filter_unchanged(auth_client, resources):
    """① 单个部门 id → 只返回该部门的资源（向后兼容）。"""
    resp = auth_client.get(f'{BASE}/resources/', {'department': 'df-a'})
    assert resp.status_code == 200, resp.content
    assert _names(resp) == {'直播间A'}


def test_multiple_departments_filter(auth_client, resources):
    """② 逗号分隔多部门 → 命中其中任一部门即返回。"""
    resp = auth_client.get(f'{BASE}/resources/', {'department': 'df-a,df-c'})
    assert resp.status_code == 200, resp.content
    assert _names(resp) == {'直播间A', '直播间C'}


def test_empty_department_param_means_no_filter(auth_client, resources):
    """③ 空参数 → 不过滤（返回全部）。"""
    resp = auth_client.get(f'{BASE}/resources/', {'department': ''})
    assert resp.status_code == 200, resp.content
    assert len(_names(resp)) == 3


def test_blank_segments_are_ignored(auth_client, resources):
    """④ 含空段（'df-a,,df-b'）→ 忽略空段，不报错。"""
    resp = auth_client.get(f'{BASE}/resources/', {'department': 'df-a,,df-b'})
    assert resp.status_code == 200, resp.content
    assert _names(resp) == {'直播间A', '直播间B'}


def test_unknown_department_id_returns_empty(auth_client, resources):
    """⑤ 不存在的部门 id → 返回空列表，不 500。"""
    resp = auth_client.get(f'{BASE}/resources/', {'department': 'no-such-dept'})
    assert resp.status_code == 200, resp.content
    assert _names(resp) == set()
