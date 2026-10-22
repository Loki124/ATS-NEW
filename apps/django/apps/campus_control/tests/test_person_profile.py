"""校招生档案详情（个人档案）—— 二期后端契约测试。

覆盖 2026-10-21 二期落地的三块能力：

1. `GET /api/v1/campus/persons/{id}/profile/` —— 档案详情聚合端点
   （信封形状 / 基础信息 / 轮岗期考核结果 / 四项统计口径）。
2. 人员列表 `?status=` 多值过滤 —— 「待入职」为单值状态（2026-10-21 兵哥口径三态收敛）。
3. 人员列表 `?mentor=` 筛选（导师）+ 性别 / 班级 / 班主任 筛选回归。

🔴 关联口径：`RotationArrangement.person_id` == `Person.user_id`
（`RotationArrangement.person_id` 是 BigInteger，语义引用校招生关联用户 id；
`Person.id` 是 nanoid，不可用于比较）。故测试中必须给 Person 落 `user_id`。
"""
import uuid

import pytest

from apps.campus_control.models import Person
from apps.campus_rotation.models import ClassRoom, RotationArrangement, RotationStage

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus'


def _uid() -> str:
    return uuid.uuid4().hex[:8]


def _make_person(user, **kwargs):
    defaults = {
        'code': f'C{_uid()}',
        'name': '张三',
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'month': '8月',
        'status': '在职',
        'created_by': user,
        'updated_by': user,
    }
    defaults.update(kwargs)
    return Person.objects.create(**defaults)


# ===================== 档案详情端点 =====================
def test_profile_returns_envelope_and_basic_info(auth_client, super_user):
    person = _make_person(
        super_user,
        name='陆翔宇',
        status='待入职',
        school_name='武汉理工大学',
        education='本科',
        phone='15800009278',
    )
    resp = auth_client.get(f'{BASE}/persons/{person.id}/profile/')
    assert resp.status_code == 200
    body = resp.json()
    assert body['success'] is True
    data = body['data']

    p = data['person']
    assert p['id'] == str(person.id)
    assert p['name'] == '陆翔宇'
    assert p['status'] == '待入职'
    assert p['schoolName'] == '武汉理工大学'
    assert p['education'] == '本科'
    assert p['phone'] == '15800009278'

    # 四项统计必须存在（无数据时为 null，前端显示「—」，不臆造 0 分）
    stats = data['stats']
    assert stats['rotationAvgScore'] is None
    assert stats['monthlyAvgScore'] is None
    assert stats['overallScore'] is None
    assert stats['rank'] is None
    assert stats['rating'] is None

    # 四个尚未建模的业务域返回空数组（前端渲染空态）
    assert data['monthlyAssessments'] == []
    assert data['dailyReports'] == []
    assert data['recommendations'] == []
    assert data['feedbacks'] == []
    assert data['stages'] == []


def test_profile_includes_class_room_and_rotation(auth_client, super_user):
    """档案详情带出班级（班主任 / HRBP / 批次）与轮岗安排 + 轮岗期考核结果。"""
    class_room = ClassRoom.objects.create(
        code=f'CL{_uid()}', name='2610 班', batch='261002',
        head_teacher=super_user, hrbp=super_user, created_by=super_user, updated_by=super_user,
    )
    person = _make_person(
        super_user, name='李四', user_id=super_user.pk, class_room=class_room,
        head_teacher=super_user, mentor=super_user,
    )
    arrangement = RotationArrangement.objects.create(
        person_id=super_user.pk, mentor=super_user, head_teacher=super_user,
        class_room=class_room, stage='PENDING', rank=3,
        created_by=super_user, updated_by=super_user,
    )
    RotationStage.objects.create(
        arrangement=arrangement, stage_no=1, mentor=super_user,
        score=95, assessment_result='优秀', created_by=super_user, updated_by=super_user,
    )

    resp = auth_client.get(f'{BASE}/persons/{person.id}/profile/')
    assert resp.status_code == 200
    data = resp.json()['data']

    assert data['classRoom']['name'] == '2610 班'
    assert data['classRoom']['batch'] == '261002'
    assert data['classRoom']['headTeacher'] == super_user.full_name
    assert data['classRoom']['hrbp'] == super_user.full_name

    assert data['rotation']['rank'] == 3
    assert data['rotation']['mentor'] == super_user.full_name

    assert len(data['stages']) == 1
    stage = data['stages'][0]
    assert stage['stageNo'] == 1
    assert stage['score'] == 95.0
    assert stage['result'] == '优秀'
    assert stage['mentor'] == super_user.full_name

    # 统计：轮岗均分 = 95；综合评分同口径；评级 95 → 优秀
    assert data['stats']['rotationAvgScore'] == 95.0
    assert data['stats']['overallScore'] == 95.0
    assert data['stats']['rating'] == '优秀'
    assert data['stats']['rank'] == 3


def test_profile_avg_score_over_multiple_stages(auth_client, super_user):
    """多段轮岗取算术平均（80 + 90 → 85）。"""
    person = _make_person(super_user, user_id=super_user.pk)
    arrangement = RotationArrangement.objects.create(
        person_id=super_user.pk, created_by=super_user, updated_by=super_user,
    )
    RotationStage.objects.create(
        arrangement=arrangement, stage_no=1, score=80,
        created_by=super_user, updated_by=super_user,
    )
    RotationStage.objects.create(
        arrangement=arrangement, stage_no=2, score=90,
        created_by=super_user, updated_by=super_user,
    )
    resp = auth_client.get(f'{BASE}/persons/{person.id}/profile/')
    data = resp.json()['data']
    assert data['stats']['rotationAvgScore'] == 85.0
    assert data['stats']['rating'] == '良好'


# ===================== 列表筛选 =====================
def test_list_multi_status_filter(auth_client, super_user):
    """?status= 多值过滤仍可用；「待入职」已是单值状态（2026-10-21 兵哥口径三态收敛）。"""
    _make_person(super_user, name='在职甲', status='在职')
    _make_person(super_user, name='待入职甲', status='待入职')
    _make_person(super_user, name='离职甲', status='离职')

    resp = auth_client.get(f'{BASE}/persons/', {'status': '待入职', 'page_size': 200})
    assert resp.status_code == 200
    names = {row['name'] for row in resp.json()['data']}
    assert names == {'待入职甲'}

    # 多值仍可用（向后兼容：逗号分隔）
    resp2 = auth_client.get(f'{BASE}/persons/', {'status': '待入职,离职', 'page_size': 200})
    assert resp2.status_code == 200
    names2 = {row['name'] for row in resp2.json()['data']}
    assert names2 == {'待入职甲', '离职甲'}


def test_list_single_status_filter_still_works(auth_client, super_user):
    """单值 ?status= 行为不变（向后兼容）。"""
    _make_person(super_user, name='在职乙', status='在职')
    _make_person(super_user, name='离职乙', status='离职')
    resp = auth_client.get(f'{BASE}/persons/', {'status': '离职', 'page_size': 200})
    names = {row['name'] for row in resp.json()['data']}
    assert names == {'离职乙'}


def test_list_mentor_filter(auth_client, super_user):
    """?mentor= 按档案级带教导师过滤。"""
    other = super_user.__class__.objects.create(
        username=f'mentor_{_uid()}', first_name='张', last_name='导师',
    )
    _make_person(super_user, name='甲班生', mentor=super_user)
    _make_person(super_user, name='乙班生', mentor=other)
    _make_person(super_user, name='无导师')

    resp = auth_client.get(f'{BASE}/persons/', {'mentor': str(super_user.pk), 'page_size': 200})
    names = {row['name'] for row in resp.json()['data']}
    assert '甲班生' in names
    assert '乙班生' not in names
    assert '无导师' not in names


def test_list_sex_class_room_head_teacher_filters(auth_client, super_user):
    """性别 / 班级 / 班主任 三个筛选同时生效。"""
    class_room = ClassRoom.objects.create(
        code=f'CL{_uid()}', name='筛选班', batch='261002',
        head_teacher=super_user, created_by=super_user, updated_by=super_user,
    )
    other = super_user.__class__.objects.create(
        username=f'ht_{_uid()}', first_name='李', last_name='班主任',
    )
    _make_person(super_user, name='命中', sex='女', class_room=class_room, head_teacher=super_user)
    _make_person(super_user, name='性别不符', sex='男', class_room=class_room, head_teacher=super_user)
    _make_person(super_user, name='班级不符', sex='女', head_teacher=super_user)

    resp = auth_client.get(f'{BASE}/persons/', {
        'sex': '女', 'class_room': str(class_room.id),
        'head_teacher': str(super_user.pk), 'page_size': 200,
    })
    names = {row['name'] for row in resp.json()['data']}
    assert '命中' in names
    assert '性别不符' not in names
    assert '班级不符' not in names


# ===================== 写入口 =====================
def test_person_create_accepts_resigned_and_new_fields(auth_client, super_user):
    """状态「离职」与二期新增字段可写入（写入口不会因枚举扩展而 400）。

    2026-10-21 兵哥口径：离职属「已入职」→ 须有工号（8 位纯数字）与实际入职日期。
    """
    payload = {
        'code': f'C{_uid()}',
        'name': '离职生',
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'month': '8月',
        'status': '离职',
        'school_name': '华中科技大学',
        'education': '硕士',
        'phone': '13800000000',
        'employee_id': '25080777',
        'actual_entry_date': '2025-08-04',
        'expected_entry_date': '2025-08-01',
    }
    resp = auth_client.post(f'{BASE}/persons/', payload)
    assert resp.status_code == 201, resp.content
    row = resp.json()['data']
    assert row['status'] == '离职'
    assert row['schoolName'] == '华中科技大学'
    assert row['education'] == '硕士'


def test_person_create_rejects_invalid_education(auth_client, super_user):
    payload = {
        'code': f'C{_uid()}',
        'name': '学历非法',
        'bu': '能电BG',
        'school': '985',
        'sex': '男',
        'major': '工学',
        'month': '8月',
        'status': '在职',
        'education': '博士后',
    }
    resp = auth_client.post(f'{BASE}/persons/', payload)
    assert resp.status_code == 400
