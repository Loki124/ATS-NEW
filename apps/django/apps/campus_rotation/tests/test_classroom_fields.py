"""班级管理字段调整（2026-10-22）后端契约测试。

覆盖三项业务变更：
1. 班级名称 = **从 1 开始的流水号**（服务端生成；新建不接收客户端传入的名字；
   编辑时不可改；非纯数字的历史班名不参与序号计算）。
2. 班级新增 `class_monitor`（班长）字段，可写可回显。
3. 「班主任 / HRBP / 批次」**模型字段保留**（hrbp 是 campus_class 行级隔离的 scope 字段，
   batch / head_teacher 仍被个人档案详情与轮岗安排表单读取），但班级管理页不再维护。
"""
import pytest

from apps.campus_rotation.models import ClassRoom

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-rotation'


def test_class_name_is_auto_sequence_from_1(auth_client):
    """新建班级 → 名称自动取 1、2、3…（客户端传的名字被忽略）。"""
    names = []
    for _ in range(3):
        resp = auth_client.post(f'{BASE}/class-rooms/', {'name': '客户端乱写的名字'}, format='json')
        assert resp.status_code == 201, resp.content
        names.append(resp.json()['data']['name'])
    assert names == ['1', '2', '3']


def test_class_name_ignores_non_numeric_legacy_names(auth_client):
    """历史遗留的非纯数字班名不参与序号计算（下一个仍是 1）。"""
    ClassRoom.objects.create(code='CL900001', name='2026校招-上海-01班')
    resp = auth_client.post(f'{BASE}/class-rooms/', {}, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['name'] == '1'


def test_class_name_continues_after_max(auth_client):
    """序号取现存纯数字班名的最大值 + 1（删掉的号不重复占用）。"""
    ClassRoom.objects.create(code='CL900002', name='7')
    resp = auth_client.post(f'{BASE}/class-rooms/', {}, format='json')
    assert resp.status_code == 201, resp.content
    assert resp.json()['data']['name'] == '8'


def test_class_name_readonly_on_update(auth_client):
    """编辑时改不动班级名称（流水号只增不改）。"""
    resp = auth_client.post(f'{BASE}/class-rooms/', {}, format='json')
    rid = resp.json()['data']['id']
    assert resp.json()['data']['name'] == '1'

    resp2 = auth_client.patch(f'{BASE}/class-rooms/{rid}/', {'name': '99'}, format='json')
    assert resp2.status_code == 200, resp2.content
    assert resp2.json()['data']['name'] == '1'


def test_class_monitor_roundtrip(auth_client, super_user):
    """班长：可写入、可回显（不强制身份 —— 班长是编排关系，不是身份准入）。"""
    resp = auth_client.post(
        f'{BASE}/class-rooms/',
        {'class_monitor': str(super_user.id)},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    assert str(data['classMonitor']) == str(super_user.id)
    assert data['classMonitorName'] == super_user.full_name


def test_legacy_fields_still_readable(auth_client, super_user):
    """班主任 / HRBP / 批次：模型字段保留，接口仍可读（个人档案与轮岗安排依赖）。"""
    from django.contrib.auth import get_user_model

    from apps.campus_rotation.seeds import seed_campus_roles
    from apps.core.models_permission_v2 import UserRoleV2

    seed_campus_roles()
    User = get_user_model()
    head_teacher = User.objects.create_user(username='ht_cls', password='Test@1234')
    UserRoleV2.objects.create(user=head_teacher, role_code='HEAD_TEACHER', system_code='recruit')

    resp = auth_client.post(
        f'{BASE}/class-rooms/',
        {
            'head_teacher': str(head_teacher.id),
            'hrbp': str(super_user.id),
            'batch': '2026秋招',
        },
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    assert data['batch'] == '2026秋招'
    assert str(data['headTeacher']) == str(head_teacher.id)
    assert str(data['hrbp']) == str(super_user.id)


# ===================== 阶段分布 + 下钻 + 班长筛选 =====================
def _make_arrangement(class_room, stage, person_id=900001):
    from apps.campus_rotation.models import RotationArrangement

    return RotationArrangement.objects.create(
        person_id=person_id, class_room=class_room, stage=stage,
        created_by=None, updated_by=None,
    )


def test_stage_counts_in_class_list(auth_client):
    """列表返回该班级的阶段分布（三态计数）。"""
    from apps.campus_rotation.models import ClassRoom

    cls = ClassRoom.objects.create(code='CL900010', name='1')
    _make_arrangement(cls, 'PENDING', 900101)
    _make_arrangement(cls, 'PENDING', 900102)
    _make_arrangement(cls, 'ONGOING', 900103)
    _make_arrangement(cls, 'DONE', 900104)

    resp = auth_client.get(f'{BASE}/class-rooms/', {'page_size': 200})
    assert resp.status_code == 200, resp.content
    row = next(r for r in resp.json()['data'] if r['id'] == str(cls.id))
    assert row['stageCounts'] == {'PENDING': 2, 'ONGOING': 1, 'DONE': 1}


def test_stage_members_drilldown(auth_client):
    """点击阶段计数 → 下钻端点返回该班级该阶段的轮岗安排明细。"""
    from apps.campus_rotation.models import ClassRoom

    cls = ClassRoom.objects.create(code='CL900011', name='2')
    _make_arrangement(cls, 'ONGOING', 900201)
    _make_arrangement(cls, 'ONGOING', 900202)
    _make_arrangement(cls, 'DONE', 900203)

    resp = auth_client.get(f'{BASE}/class-rooms/{cls.id}/stage-members/', {'stage': 'ONGOING'})
    assert resp.status_code == 200, resp.content
    data = resp.json()['data']
    assert data['stage'] == 'ONGOING'
    assert data['stageLabel'] == '轮岗中'
    assert data['total'] == 2
    assert len(data['items']) == 2


def test_stage_members_rejects_bad_stage(auth_client):
    from apps.campus_rotation.models import ClassRoom

    cls = ClassRoom.objects.create(code='CL900012', name='3')
    resp = auth_client.get(f'{BASE}/class-rooms/{cls.id}/stage-members/', {'stage': 'BOGUS'})
    assert resp.status_code == 400
    assert 'PENDING' in str(resp.json())


def test_filter_by_class_monitor(auth_client, super_user):
    """班长筛选：按 class_monitor 过滤班级。"""
    from apps.campus_rotation.models import ClassRoom

    other = super_user.__class__.objects.create_user(username='mon_other', password='Test@1234')
    a = ClassRoom.objects.create(code='CL900013', name='1', class_monitor=super_user)
    ClassRoom.objects.create(code='CL900014', name='2', class_monitor=other)

    resp = auth_client.get(f'{BASE}/class-rooms/', {'class_monitor': str(super_user.id), 'page_size': 200})
    assert resp.status_code == 200
    ids = {r['id'] for r in resp.json()['data']}
    assert str(a.id) in ids
    assert str(other.id) not in ids

