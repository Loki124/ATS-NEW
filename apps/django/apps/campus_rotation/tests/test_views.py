"""campus_rotation 后端冒烟测试（Batch 0）。

覆盖三张表的 CRUD 冒烟 + BU 二级部门深度校验 + 软删/恢复 + V2 权限接线。
fixtures（auth_client / auth_hr_client / department / super_user 等）来自
tests/fixtures_common（经顶层 conftest.py 以 plugin 身份全局加载）。

关于 BU 深度：is_bu_depth(dept) = `dept.parent_id IS NOT NULL AND
dept.parent.parent_id IS NULL`。即「parent 存在、且 parent 的 parent 不存在」的节点，
对应 0 索引树 root(0) -> bu_valid(1) -> bu_deep(2)。故命中校验的是 bu_valid
（其 parent=root，root 无 parent），bu_deep 因 grandparent 存在而不命中。

入参统一用 snake_case（camel-case 解析器对下划线字段透传），断言只看状态码 /
success 信封 / id（单字字段不分词）。
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.campus_rotation.seeds import (
    seed_campus_roles,
    seed_live_room_platform_type,
    seed_location_type,
)
from apps.core.models import Department, User
from apps.core.models_permission_v2 import UserRoleV2

BASE = '/api/v1/campus-rotation'


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #
@pytest.fixture
def _seed_campus_data(db):
    """确保校招轮岗角色与字典种子就绪（测试库幂等）。"""
    seed_campus_roles()
    seed_live_room_platform_type()
    seed_location_type()


@pytest.fixture
def bu_hierarchy(db):
    """构建部门树：root(0) -> bu_valid(1, 二级部门) -> bu_deep(2, 三级部门)。

    bu_valid 命中 is_bu_depth（parent 存在、parent.parent 为 None）；bu_deep 因
    grandparent 存在而不命中。
    """
    root = Department.objects.create(id='dept-root', name='集团', code='ROOT', path='/集团')
    bu_valid = Department.objects.create(
        id='dept-bu', name='技术BU', code='BU', parent=root, path='/集团/技术BU',
    )
    bu_deep = Department.objects.create(
        id='dept-deep', name='技术BU-子', code='DEEP', parent=bu_valid,
        path='/集团/技术BU/子',
    )
    return {'root': root, 'bu_valid': bu_valid, 'bu_deep': bu_deep}


def _attach_campus_role(user, role_code):
    UserRoleV2.objects.create(user=user, role_code=role_code, system_code='recruit')


@pytest.fixture
def mentor_user(db, _seed_campus_data):
    u = User.objects.create_user(username='mentor_rot', password='Test@1234', employee_id='M-ROT')
    _attach_campus_role(u, 'CAMPUS_MENTOR')
    return u


@pytest.fixture
def head_teacher_user(db, _seed_campus_data):
    u = User.objects.create_user(username='ht_rot', password='Test@1234', employee_id='H-ROT')
    _attach_campus_role(u, 'HEAD_TEACHER')
    return u


def _client_for(user):
    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client


# --------------------------------------------------------------------------- #
# LiveRoom
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestLiveRoomCRUD:
    def test_create_requires_platform_dict(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu = bu_hierarchy['bu_valid']
        # platform 必须是启用字典项，非法值应被校验拒绝
        resp = auth_client.post(
            f'{BASE}/live-rooms/',
            {'name': '直播间A', 'platform': 'NOT_A_PLATFORM', 'bu': bu.id},
            format='json',
        )
        assert resp.status_code == 400

    def test_create_and_retrieve(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu = bu_hierarchy['bu_valid']
        resp = auth_client.post(
            f'{BASE}/live-rooms/',
            {'name': '直播间A', 'platform': 'VIDEO_ACCOUNT', 'location': 'BEIJING', 'bu': bu.id},
            format='json',
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body['success'] is True
        lid = body['data']['id']
        assert body['data'].get('roomNo')  # 自动补号 LRxxxxxx
        assert 'campusCount' in body['data']  # 只读聚合字段

        # 详情
        resp = auth_client.get(f'{BASE}/live-rooms/{lid}/')
        assert resp.status_code == 200
        assert resp.json()['data']['id'] == lid

    def test_list_and_filter(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu = bu_hierarchy['bu_valid']
        auth_client.post(
            f'{BASE}/live-rooms/',
            {'name': '直播间B', 'platform': 'TENCENT_MEETING', 'bu': bu.id},
            format='json',
        )
        resp = auth_client.get(f'{BASE}/live-rooms/', {'bu': bu.id})
        assert resp.status_code == 200
        # 列表经信封包裹：{success, data:[...], ...}
        assert 'data' in resp.json()
        assert isinstance(resp.json()['data'], list)

    def test_update_and_soft_delete_restore(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu = bu_hierarchy['bu_valid']
        resp = auth_client.post(
            f'{BASE}/live-rooms/',
            {'name': '直播间C', 'platform': 'WECHAT_WORK_LIVE', 'bu': bu.id},
            format='json',
        )
        lid = resp.json()['data']['id']

        resp = auth_client.patch(f'{BASE}/live-rooms/{lid}/', {'name': '直播间C改'}, format='json')
        assert resp.status_code == 200
        assert resp.json()['data']['name'] == '直播间C改'

        resp = auth_client.delete(f'{BASE}/live-rooms/{lid}/')
        assert resp.status_code == 200

        # 软删后列表不出现
        resp = auth_client.get(f'{BASE}/live-rooms/', {'search': '直播间C改'})
        assert resp.json()['data'] == []

        # 恢复（restore 须能定位软删对象）
        resp = auth_client.post(f'{BASE}/live-rooms/{lid}/restore/')
        assert resp.status_code == 200
        assert resp.json()['success'] is True

        # 恢复后列表可见
        resp = auth_client.get(f'{BASE}/live-rooms/', {'search': '直播间C改'})
        assert len(resp.json()['data']) == 1


# --------------------------------------------------------------------------- #
# ClassRoom
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestClassRoomCRUD:
    def test_create_requires_head_teacher_role(self, auth_client, _seed_campus_data):
        # head_teacher 若提供必须是 HEAD_TEACHER 身份；先建一个无角色用户
        plain = User.objects.create_user(username='plain_teacher', password='x', employee_id='PT')
        resp = auth_client.post(
            f'{BASE}/class-rooms/',
            {'name': '班级A', 'head_teacher': plain.id},
            format='json',
        )
        assert resp.status_code == 400

    def test_create_and_crud(self, auth_client, head_teacher_user, _seed_campus_data):
        resp = auth_client.post(
            f'{BASE}/class-rooms/',
            {'name': '班级A', 'head_teacher': head_teacher_user.id, 'batch': '2026春'},
            format='json',
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body['success'] is True
        cid = body['data']['id']
        assert body['data'].get('code')  # 自动补号 CLxxxxxx
        assert 'studentCount' in body['data']

        resp = auth_client.get(f'{BASE}/class-rooms/{cid}/')
        assert resp.status_code == 200

        resp = auth_client.patch(f'{BASE}/class-rooms/{cid}/', {'name': '班级A改'}, format='json')
        assert resp.status_code == 200

        resp = auth_client.delete(f'{BASE}/class-rooms/{cid}/')
        assert resp.status_code == 200

        resp = auth_client.post(f'{BASE}/class-rooms/{cid}/restore/')
        assert resp.status_code == 200


# --------------------------------------------------------------------------- #
# RotationArrangement
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestRotationArrangementCRUD:
    def test_create_and_crud(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu = bu_hierarchy['bu_valid']
        resp = auth_client.post(
            f'{BASE}/rotation-arrangements/',
            {'person_id': 100001, 'intent_bu': bu.code},
            format='json',
        )
        assert resp.status_code == 201, resp.content
        body = resp.json()
        assert body['success'] is True
        rid = body['data']['id']

        resp = auth_client.get(f'{BASE}/rotation-arrangements/{rid}/')
        assert resp.status_code == 200

        resp = auth_client.patch(
            f'{BASE}/rotation-arrangements/{rid}/',
            {'stage': 'ONGOING', 'employee_status': 'ACTIVE'},
            format='json',
        )
        assert resp.status_code == 200

        resp = auth_client.delete(f'{BASE}/rotation-arrangements/{rid}/')
        assert resp.status_code == 200

        resp = auth_client.post(f'{BASE}/rotation-arrangements/{rid}/restore/')
        assert resp.status_code == 200

    def test_batch_assign(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu = bu_hierarchy['bu_valid']
        resp = auth_client.post(
            f'{BASE}/rotation-arrangements/',
            {'person_id': 100002, 'intent_bu': bu.code},
            format='json',
        )
        rid = resp.json()['data']['id']
        resp = auth_client.post(
            f'{BASE}/rotation-arrangements/batch-assign/',
            {'ids': [rid], 'stage': 'APPROVING'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.json()['data']['updated'] == 1


# --------------------------------------------------------------------------- #
# BU 二级部门深度校验
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestBuDepthValidation:
    def test_bu_must_be_second_level(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu_valid = bu_hierarchy['bu_valid']   # 命中 is_bu_depth -> 合法
        bu_deep = bu_hierarchy['bu_deep']     # grandparent 存在 -> 非法

        # 非法：三级部门作 BU
        resp = auth_client.post(
            f'{BASE}/live-rooms/',
            {'name': '违规直播间', 'platform': 'VIDEO_ACCOUNT', 'bu': bu_deep.id},
            format='json',
        )
        assert resp.status_code == 400

        # 合法：二级部门作 BU
        resp = auth_client.post(
            f'{BASE}/live-rooms/',
            {'name': '合规直播间', 'platform': 'VIDEO_ACCOUNT', 'bu': bu_valid.id},
            format='json',
        )
        assert resp.status_code == 201, resp.content

    def test_rotation_intent_bu_depth(self, auth_client, bu_hierarchy, _seed_campus_data):
        bu_valid = bu_hierarchy['bu_valid']
        bu_deep = bu_hierarchy['bu_deep']

        # 非法：三级部门作 intent_bu
        resp = auth_client.post(
            f'{BASE}/rotation-arrangements/',
            {'person_id': 100003, 'intent_bu': bu_deep.code},
            format='json',
        )
        assert resp.status_code == 400

        # 合法：二级部门作 intent_bu
        resp = auth_client.post(
            f'{BASE}/rotation-arrangements/',
            {'person_id': 100004, 'intent_bu': bu_valid.code},
            format='json',
        )
        assert resp.status_code == 201, resp.content


# --------------------------------------------------------------------------- #
# V2 权限接线
# --------------------------------------------------------------------------- #
@pytest.mark.django_db
class TestV2PermissionWiring:
    def test_plain_user_denied(self, db, _seed_campus_data):
        plain = User.objects.create_user(username='plain_rot', password='x', employee_id='PR')
        client = _client_for(plain)
        resp = client.get(f'{BASE}/live-rooms/')
        assert resp.status_code == 403

    def test_hr_user_allowed(self, auth_hr_client, _seed_campus_data):
        resp = auth_hr_client.get(f'{BASE}/live-rooms/')
        assert resp.status_code == 200
