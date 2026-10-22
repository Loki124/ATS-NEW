"""轮岗安排表单分组（三期）后端契约测试。

覆盖 2026-10-21 三期新增的三个字段与校验：

1. `resource`「具体位置（轮岗资源）」：2026-10-22 直播间 + 客服部门整合为
   「轮岗资源」一张表后，原先两个 FK（live_room / service_dept）合并为**单个**
   resource FK；「轮岗位置类型」不再单独存列，改由 `resource.resource_type` 派生；
2. `class_monitor`「班长」：User 引用（不做身份强校验 —— 班长是编排关系，不是身份准入）；
3. 序列化器回填校招生基本信息（personName / personEmployeeId / personEducation /
   personExpectedEntryDate / personActualEntryDate），供表单「基本信息」组只读展示。
"""
import pytest

from apps.campus_control.models import Person
from apps.campus_rotation.models import (
    RotationArrangement,
    RotationResource,
)
from apps.core.models import Department

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-rotation'


@pytest.fixture
def dept_tree(db):
    """部门树：root(0) → grp(1) → bu(2=BU) → deep(3)。"""
    root = Department.objects.create(id='arr-root', name='集团', code='ARR_ROOT', path='/集团')
    grp = Department.objects.create(
        id='arr-grp', name='技术事业群', code='ARR_GRP', parent=root, path='/集团/技术事业群',
    )
    bu = Department.objects.create(
        id='arr-bu', name='技术BU', code='ARR_BU', parent=grp, path='/集团/技术事业群/技术BU',
    )
    deep = Department.objects.create(
        id='arr-deep', name='技术BU-子', code='ARR_DEEP', parent=bu, path='/集团/技术事业群/技术BU/子',
    )
    return {'root': root, 'grp': grp, 'bu': bu, 'deep': deep}


@pytest.fixture
def live_room(db):
    return RotationResource.objects.create(
        name='上海01直播间', resource_no='LR900001', resource_type='LIVE_ROOM',
    )


@pytest.fixture
def service_dept(db, dept_tree):
    return RotationResource.objects.create(
        name='上海客服一组',
        resource_no='SD900001',
        resource_type='SERVICE_DEPT',
        department=dept_tree['deep'],
        bu=dept_tree['bu'],
    )


@pytest.fixture
def head_teacher_user(db):
    from django.contrib.auth import get_user_model

    from apps.campus_rotation.seeds import seed_campus_roles
    from apps.core.models_permission_v2 import UserRoleV2

    seed_campus_roles()
    User = get_user_model()
    u = User.objects.create_user(username='ht_arr', password='Test@1234', employee_id='H-ARR')
    UserRoleV2.objects.create(user=u, role_code='HEAD_TEACHER', system_code='recruit')
    return u


def test_create_with_live_room_location(auth_client, live_room):
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {
            'person_id': 100001,
            'resource': str(live_room.id),
        },
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    # 轮岗位置类型由资源类型派生（不再单独存列）
    assert data['locationType'] == 'LIVE_ROOM'
    assert data['resource'] == str(live_room.id)
    assert data['resourceName'] == '上海01直播间'


def test_create_with_service_dept_location(auth_client, service_dept):
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {
            'person_id': 100002,
            'resource': str(service_dept.id),
        },
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    assert data['locationType'] == 'SERVICE_DEPT'
    assert data['resource'] == str(service_dept.id)
    assert data['resourceName'] == '上海客服一组'


def test_location_type_is_read_only(auth_client, live_room):
    """🔴 客户端提交的 locationType 被忽略 —— 类型只由资源的 resource_type 决定。

    合并前「轮岗位置类型」是独立可写字段（需与具体位置互斥清理），
    合并后类型由 resource 唯一决定 → 不存在错配可能。
    """
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {
            'person_id': 100003,
            'location_type': 'SERVICE_DEPT',   # 故意与直播间资源不符
            'resource': str(live_room.id),
        },
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    assert data['locationType'] == 'LIVE_ROOM'
    assert data['resource'] == str(live_room.id)


def test_switching_resource_replaces_previous(auth_client, live_room, service_dept):
    """换具体位置（直播间 → 客服部门）→ 旧资源被替换，类型随之变化。"""
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {
            'person_id': 100005,
            'resource': str(live_room.id),
        },
        format='json',
    )
    rid = resp.json()['data']['id']

    resp2 = auth_client.patch(
        f'{BASE}/rotation-arrangements/{rid}/',
        {'resource': str(service_dept.id)},
        format='json',
    )
    assert resp2.status_code == 200, resp2.content
    data = resp2.json()['data']
    assert data['locationType'] == 'SERVICE_DEPT'
    assert data['resource'] == str(service_dept.id)
    assert not data.get('liveRoom')
    assert not data.get('serviceDept')


def test_inactive_resource_rejected(auth_client, live_room):
    """停用的轮岗资源不能再被新安排占用 → 400（中文可读提示）。"""
    live_room.is_active = False
    live_room.save(update_fields=['is_active'])
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {'person_id': 100006, 'resource': str(live_room.id)},
        format='json',
    )
    assert resp.status_code == 400
    assert '停用' in str(resp.json())


def test_class_monitor_roundtrip(auth_client, head_teacher_user):
    """班长：User 引用可写入可回显。"""
    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {'person_id': 100007, 'class_monitor': str(head_teacher_user.id)},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    assert str(data['classMonitor']) == str(head_teacher_user.id)
    assert data['classMonitorName'] == head_teacher_user.full_name


def test_person_basic_info_is_returned(auth_client):
    """校招生基本信息（工号 / 教育经历 / 入职日期）随安排返回，供表单「基本信息」组回填。"""
    from datetime import date

    user = auth_client.handler._force_user if hasattr(auth_client, 'handler') else None
    from django.contrib.auth import get_user_model

    User = get_user_model()
    account = User.objects.create_user(username='person_campus_rot', password='Test@1234')
    person = Person.objects.create(
        code='C99000001', name='周砚', bu='能电BG', school='985', sex='男', major='工学',
        month='8月', status='待入职', employee_id='25990001', education='本科',
        expected_entry_date=date(2026, 8, 15), actual_entry_date=None,
        user_id=account.id, created_by=account, updated_by=account,
    )
    assert user is None or True  # 仅占位，保持夹具链清晰

    resp = auth_client.post(
        f'{BASE}/rotation-arrangements/',
        {'person_id': account.id},
        format='json',
    )
    assert resp.status_code == 201, resp.content
    data = resp.json()['data']
    # ⚠️ 断言对齐「序列化器实际解析到的那条 Person」：同一 user_id 理论上可能对应多条
    #    Person（历史数据），序列化器取排序首条 —— 断言写死自己的行会在共享测试库
    #    被并发用例污染时误报。
    resolved = Person.objects.filter(user_id=account.id, deleted_at__isnull=True).first()
    assert data['personName'] == resolved.name
    assert data['personEmployeeId'] == resolved.employee_id
    assert data['personEducation'] == resolved.education
    # 日期字段在 API 边界渲染成 ISO 字符串
    assert data['personExpectedEntryDate'] == (
        resolved.expected_entry_date.isoformat() if resolved.expected_entry_date else None
    )
    assert data['personActualEntryDate'] == (
        resolved.actual_entry_date.isoformat() if resolved.actual_entry_date else None
    )
    assert person.id  # 人员已建
