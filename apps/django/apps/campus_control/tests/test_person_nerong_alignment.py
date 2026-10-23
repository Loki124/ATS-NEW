"""校招生管理模块对齐聂荣《校招生管理系统 - 需求文档》（2026-10-23）口径的护栏。

需求文档里「轮岗资源」「轮岗安排」两个模块的规则，反向约束「校招生管理（人员管理）」模块。
本文件锁住落到人员管理侧的**行为**，每条用例注明需求原文。

覆盖：

1. 批次**自动生成**（基于入职时间，月中 15 号为界）——「批次（基于入职时间自动生成…）」；
2. 人工填过的批次**不被**自动值覆盖（批次在编辑弹窗里可改）；
3. 列表下发**简历编号**（`code`）与**班长**——「包含字段：姓名、简历编号、员工工号、…、班长、HRBP…」；
4. 身份字段**完整性标记**——「简历编号与员工工号应取尽取…其他必须完整」；
5. 取数**数据范围**（26 年及以后入职或预计入职）——「数据范围（26年及以后入职或预计入职数据）」；
6. **班长筛选**；
7. **班长自动带出**（基于班级）——「班长（基于班级自动带出可修改）」；
8. **HRBP 自动填充**（轮岗 BU 部门的 HRBP）——「HRBP（基于轮岗BU部门的HRBP自动填充，可修改）」；
9. **当前轮岗部门**取轮岗资源所在 BU——「当前轮岗部门（基于轮岗的直播间取所在BU部门）」；
10. **一键成班**——「班级（按照当前批次每30-35人成立一个班级…）」；
11. 教育经历**院校标签就高原则**——「教育经历（院校标签就高原则对应的教育经历…）」。
"""
import random
import uuid
from datetime import date

import pytest

from apps.campus_control.models import Person, PersonEducation
from apps.campus_control.education import pick_top_education
from apps.campus_rotation.models import ClassRoom, RotationArrangement, RotationResource
from apps.core.models import Department, User

BASE = '/api/v1/campus'


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _emp_id():
    return f'{random.randint(10**7, 10**8 - 1):08d}'


def _make_person(user, **kwargs):
    data = dict(
        code=f'C{_uid()}', name='张三', bu='能电BG', school='985', sex='男',
        major='工学', month='1月', status='在职', created_by=user, updated_by=user,
        employee_id=_emp_id(), actual_entry_date=date(2026, 7, 1),
        expected_entry_date=date(2026, 7, 1),
    )
    data.update(kwargs)
    return Person.objects.create(**data)


def _make_bu(user, hrbp=None, suffix='bu'):
    """造一棵 根 → 事业群 → BU 的部门树（BU = 0 基层级 depth==2）。"""
    root = Department.objects.create(
        id=f'root-{suffix}', name=f'根-{suffix}', code=f'ROOT_{suffix}', path=f'/根-{suffix}',
    )
    bg = Department.objects.create(
        id=f'bg-{suffix}', name=f'事业群-{suffix}', code=f'BG_{suffix}',
        path=f'/根-{suffix}/事业群-{suffix}', parent=root,
    )
    bu = Department.objects.create(
        id=f'bu-{suffix}', name=f'BU-{suffix}', code=f'BU_{suffix}',
        path=f'/根-{suffix}/事业群-{suffix}/BU-{suffix}', parent=bg, hrbp=hrbp,
    )
    return bu


def _make_resource(user, bu, name='直播间A'):
    return RotationResource.objects.create(
        name=name, resource_type='LIVE_ROOM', department=bu, bu=bu,
        capacity=10, social_count=1, created_by=user, updated_by=user,
    )


# ---------------------------------------------------------------------------
# ① 批次自动生成
# ---------------------------------------------------------------------------

class TestBatchAutofill:
    """批次基于入职时间自动生成；人工填过的不覆盖。"""

    def test_按实际入职日期生成(self, super_user):
        p = _make_person(super_user, actual_entry_date=date(2026, 7, 20))
        assert p.batch == '260702'

    def test_15号及以前为01期(self, super_user):
        p = _make_person(super_user, actual_entry_date=date(2026, 7, 15))
        assert p.batch == '260701'

    def test_待入职按预计入职日期生成(self, super_user):
        p = _make_person(
            super_user, status='待入职', employee_id='', actual_entry_date=None,
            expected_entry_date=date(2026, 8, 3),
        )
        assert p.batch == '260801'

    def test_历史入职段固定号(self, super_user):
        p1 = _make_person(super_user, actual_entry_date=date(2026, 2, 10))
        p2 = _make_person(super_user, actual_entry_date=date(2026, 5, 20))
        assert p1.batch == '260001'
        assert p2.batch == '260002'

    def test_人工填的批次不被覆盖(self, super_user):
        p = _make_person(super_user, actual_entry_date=date(2026, 7, 20), batch='自定义批次')
        assert p.batch == '自定义批次'
        p.actual_entry_date = date(2026, 8, 20)
        p.save()
        assert p.batch == '自定义批次'

    def test_无入职日期不臆造批次(self, super_user):
        p = _make_person(
            super_user, actual_entry_date=None, expected_entry_date=None,
        )
        assert p.batch == ''


# ---------------------------------------------------------------------------
# ② 列表字段下发（简历编号 / 班长 / 完整性标记）
# ---------------------------------------------------------------------------

class TestListFields:
    """列表补齐聂荣口径的字段。"""

    def test_下发简历编号与班长(self, auth_client, super_user):
        monitor = User.objects.create_user(
            username=f'monitor_{_uid()}', password='Test@1234', first_name='班', last_name='长',
        )
        p = _make_person(super_user)
        p.class_monitor = monitor
        p.save()
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
        assert resp.status_code == 200
        row = next(r for r in resp.json()['data'] if r['id'] == str(p.id))
        # 简历编号 = 档案编号 code（编辑弹窗里已沿用该命名）
        assert row['code'] == p.code
        assert row['classMonitorName'] == monitor.full_name

    def test_在职缺工号标记为不完整(self, auth_client, super_user):
        p = _make_person(super_user, employee_id='')
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
        row = next(r for r in resp.json()['data'] if r['id'] == str(p.id))
        assert row['identityIncomplete'] is True

    def test_待入职缺工号不算不完整(self, auth_client, super_user):
        p = _make_person(
            super_user, status='待入职', employee_id='', actual_entry_date=None,
        )
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
        row = next(r for r in resp.json()['data'] if r['id'] == str(p.id))
        assert row['identityIncomplete'] is False


# ---------------------------------------------------------------------------
# ③ 取数数据范围
# ---------------------------------------------------------------------------

class TestDataScope:
    """数据范围：26 年及以后入职或预计入职。"""

    def test_26年前入职被排除(self, auth_client, super_user):
        old = _make_person(
            super_user, actual_entry_date=date(2025, 8, 1), expected_entry_date=date(2025, 8, 1),
        )
        new = _make_person(super_user, actual_entry_date=date(2026, 8, 1))
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
        ids = {r['id'] for r in resp.json()['data']}
        assert str(old.id) not in ids
        assert str(new.id) in ids

    def test_两个日期都空的人保留(self, auth_client, super_user):
        p = _make_person(super_user, actual_entry_date=None, expected_entry_date=None)
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
        ids = {r['id'] for r in resp.json()['data']}
        assert str(p.id) in ids

    def test_可显式查全部(self, auth_client, super_user):
        old = _make_person(super_user, actual_entry_date=date(2025, 8, 1))
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200, 'entry_scope': 'all'})
        ids = {r['id'] for r in resp.json()['data']}
        assert str(old.id) in ids


# ---------------------------------------------------------------------------
# ④ 班长筛选 + 自动带出
# ---------------------------------------------------------------------------

class TestClassMonitor:
    """班长：可筛选；按班级自动带出。"""

    def test_按班长筛选(self, auth_client, super_user):
        monitor = User.objects.create_user(
            username=f'mon_{_uid()}', password='Test@1234', first_name='王', last_name='五',
        )
        other = User.objects.create_user(
            username=f'mon2_{_uid()}', password='Test@1234', first_name='赵', last_name='六',
        )
        p1 = _make_person(super_user, class_monitor=monitor)
        _make_person(super_user, class_monitor=other)
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200, 'class_monitor': monitor.id})
        ids = {r['id'] for r in resp.json()['data']}
        assert ids == {str(p1.id)}

    def test_保存时按班级自动带出班长(self, auth_client, super_user):
        monitor = User.objects.create_user(
            username=f'mon3_{_uid()}', password='Test@1234', first_name='孙', last_name='七',
        )
        classroom = ClassRoom.objects.create(
            name='260701-01', batch='260701', class_monitor=monitor,
            created_by=super_user, updated_by=super_user,
        )
        p = _make_person(super_user, class_room=classroom)
        assert p.class_monitor_id is None  # 建档时未指定 → 不自动填

        resp = auth_client.put(
            f'{BASE}/persons/{p.id}/',
            {
                'name': p.name, 'bu': p.bu, 'school': p.school, 'sex': p.sex,
                'major': p.major, 'status': p.status, 'employee_id': p.employee_id,
                'actual_entry_date': '2026-07-01', 'expected_entry_date': '2026-07-01',
                'class_room': str(classroom.id),
            },
            format='json',
        )
        assert resp.status_code == 200, resp.content
        p.refresh_from_db()
        assert p.class_monitor_id == monitor.id


# ---------------------------------------------------------------------------
# ⑤ HRBP 自动填充 + 当前轮岗部门取轮岗资源 BU
# ---------------------------------------------------------------------------

class TestRotationDeptAndHrbp:
    """当前轮岗部门 = 轮岗资源所在 BU；HRBP 自动取该 BU 的部门 HRBP。"""

    def test_当前轮岗部门取轮岗资源BU(self, auth_client, super_user):
        hrbp_user = User.objects.create_user(
            username=f'hrbp_{_uid()}', password='Test@1234', first_name='胡', last_name='八',
        )
        bu = _make_bu(super_user, hrbp=hrbp_user, suffix='nerong1')
        resource = _make_resource(super_user, bu)
        p = _make_person(super_user)
        RotationArrangement.objects.create(
            campus_person=p, resource=resource, current_dept=bu,
            stage='ONGOING', created_by=super_user, updated_by=super_user,
        )
        resp = auth_client.get(f'{BASE}/persons/', {'page_size': 200})
        row = next(r for r in resp.json()['data'] if r['id'] == str(p.id))
        assert row['rotationDept'] == bu.name
        # HRBP 自动填充：未人工指定时，列表下发的 hrbp 即该 BU 的部门 HRBP
        assert row['hrbpName'] == hrbp_user.full_name

    def test_保存时回填HRBP(self, auth_client, super_user):
        hrbp_user = User.objects.create_user(
            username=f'hrbp2_{_uid()}', password='Test@1234', first_name='陆', last_name='九',
        )
        bu = _make_bu(super_user, hrbp=hrbp_user, suffix='nerong2')
        resource = _make_resource(super_user, bu, name='直播间B')
        p = _make_person(super_user)
        RotationArrangement.objects.create(
            campus_person=p, resource=resource, current_dept=bu,
            stage='ONGOING', created_by=super_user, updated_by=super_user,
        )
        resp = auth_client.put(
            f'{BASE}/persons/{p.id}/',
            {
                'name': p.name, 'bu': p.bu, 'school': p.school, 'sex': p.sex,
                'major': p.major, 'status': p.status, 'employee_id': p.employee_id,
                'actual_entry_date': '2026-07-01', 'expected_entry_date': '2026-07-01',
            },
            format='json',
        )
        assert resp.status_code == 200, resp.content
        p.refresh_from_db()
        assert p.hrbp_id == hrbp_user.id


# ---------------------------------------------------------------------------
# ⑥ 一键成班
# ---------------------------------------------------------------------------

class TestFormClasses:
    """一键成班：按批次把未分班人员按成班方案挂进班级。"""

    def test_成班后人数守恒(self, auth_client, super_user):
        batch = '260701'
        people = [
            _make_person(super_user, batch=batch, class_room=None) for _ in range(65)
        ]
        resp = auth_client.post(
            f'{BASE}/persons/form-classes/', {'batch': batch}, format='json',
        )
        assert resp.status_code == 200, resp.content
        data = resp.json()['data']
        assert data['total'] == 65
        assert data['sizes'] == [33, 32]
        # 所有人都有班级，且分班人数守恒
        assigned = Person.objects.filter(
            id__in=[p.id for p in people], class_room__isnull=False,
        ).count()
        assert assigned == 65
        rooms = ClassRoom.objects.filter(batch=batch)
        assert rooms.count() == 2
        assert sum(r.persons.count() for r in rooms) == 65

    def test_幂等_已分班的人不重复分(self, auth_client, super_user):
        batch = '260702'
        _make_person(super_user, batch=batch)
        auth_client.post(f'{BASE}/persons/form-classes/', {'batch': batch}, format='json')
        resp = auth_client.post(
            f'{BASE}/persons/form-classes/', {'batch': batch}, format='json',
        )
        assert resp.status_code == 200
        # 第二次没有待分人员 → 不再建班
        assert resp.json()['data']['total'] == 0

    def test_缺批次报400(self, auth_client, super_user):
        resp = auth_client.post(f'{BASE}/persons/form-classes/', {}, format='json')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# ⑦ 教育经历「院校标签就高原则」
# ---------------------------------------------------------------------------

class TestEducationTopPick:
    """档案详情的教育经历按院校标签就高原则取用。"""

    def test_按院校标签取最高(self):
        records = [
            PersonEducation(school_tag='211', education='本科', created_at=date(2026, 1, 1)),
            PersonEducation(school_tag='985', education='硕士', created_at=date(2026, 1, 2)),
            PersonEducation(school_tag='双一流', education='本科', created_at=date(2026, 1, 3)),
        ]
        assert pick_top_education(records).school_tag == '985'

    def test_标签相同取学历高(self):
        records = [
            PersonEducation(school_tag='985', education='本科', created_at=date(2026, 1, 1)),
            PersonEducation(school_tag='985', education='博士', created_at=date(2026, 1, 2)),
        ]
        assert pick_top_education(records).education == '博士'

    def test_无记录返回None(self):
        assert pick_top_education([]) is None

    def test_档案详情回传教育经历(self, auth_client, super_user):
        p = _make_person(super_user)
        PersonEducation.objects.create(
            person=p, school_name='某某大学', school_tag='211',
            major_name='计算机', education='本科', created_by=super_user, updated_by=super_user,
        )
        PersonEducation.objects.create(
            person=p, school_name='某某985', school_tag='985',
            major_name='软件工程', education='硕士', created_by=super_user, updated_by=super_user,
        )
        resp = auth_client.get(f'{BASE}/persons/{p.id}/profile/')
        assert resp.status_code == 200
        data = resp.json()['data']
        assert len(data['educations']) == 2
        # 就高原则：985 那条（响应键由全局渲染器统一转 camelCase）
        assert data['person']['schoolName'] == '某某985'
        assert data['person']['majorName'] == '软件工程'
        assert data['person']['education'] == '硕士'
