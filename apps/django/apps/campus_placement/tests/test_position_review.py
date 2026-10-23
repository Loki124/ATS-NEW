"""岗位需求审核与开放判定（逆向清单 §4.3）。

- 审核流：待审核 → 已通过 / 已驳回；HRBP 可撤回；管理员审核发布；
- **岗位开放判定顺序**（逆向清单 §4.3，顺序固定）：
  审核状态 → 开放开关 → 发布范围(all/batch/intentDept) → 面向届数/班级 → 窗口期。
"""
from datetime import date

import pytest

from apps.campus_control.models import Person
from apps.campus_placement.models import PositionDemand
from apps.campus_placement.views import _position_open_state

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-placement'


def _person(code, name, batch='B2026', intent_bu='能电BG', **kw):
    return Person.objects.create(
        code=code, name=name, bu='能电BG', school='985', sex='男', major='工学',
        status='在职', batch=batch, intent_bu=intent_bu, **kw,
    )


def _demand(**kw):
    defaults = {
        'name': '客服部 · 直播运营',
        'dept': '客服部',
        'business_dept': '能电BG',
        'headcount': 2,
        'need_status': PositionDemand.NeedStatus.PUBLISHED,
        'scope_type': PositionDemand.ScopeType.ALL,
        'open_enabled': True,
        'open_start': date(2026, 1, 1),
        'open_end': date(2026, 12, 31),
    }
    defaults.update(kw)
    return PositionDemand.objects.create(**defaults)


class Test需求审核:
    """需求审核流（逆向清单 §4.3「岗位审核流」）。"""

    def test_审核通过(self, auth_client, db):
        demand = _demand(need_status=PositionDemand.NeedStatus.PENDING)
        r = auth_client.post(
            f'{BASE}/position-demands/{demand.id}/review/',
            {'action': 'approve', 'note': '同意'},
            format='json',
        )
        assert r.status_code == 200
        demand.refresh_from_db()
        assert demand.need_status == PositionDemand.NeedStatus.APPROVED

    def test_审核驳回(self, auth_client, db):
        demand = _demand(need_status=PositionDemand.NeedStatus.PENDING)
        r = auth_client.post(
            f'{BASE}/position-demands/{demand.id}/review/',
            {'action': 'reject', 'note': '编制不足'},
            format='json',
        )
        assert r.status_code == 200
        demand.refresh_from_db()
        assert demand.need_status == PositionDemand.NeedStatus.REJECTED

    def test_非法审核动作被拒(self, auth_client, db):
        demand = _demand(need_status=PositionDemand.NeedStatus.PENDING)
        r = auth_client.post(
            f'{BASE}/position-demands/{demand.id}/review/',
            {'action': 'unknown'},
            format='json',
        )
        assert r.status_code == 400
        assert 'approve' in str(r.data)

    def test_hrbp撤回需求回到待审核(self, auth_client, db):
        demand = _demand(need_status=PositionDemand.NeedStatus.APPROVED)
        r = auth_client.post(
            f'{BASE}/position-demands/{demand.id}/withdraw/', {}, format='json',
        )
        assert r.status_code == 200
        demand.refresh_from_db()
        assert demand.need_status == PositionDemand.NeedStatus.PENDING
        assert demand.open_enabled is False

    def test_发布需求(self, auth_client, db):
        demand = _demand(need_status=PositionDemand.NeedStatus.APPROVED)
        r = auth_client.post(
            f'{BASE}/position-demands/{demand.id}/publish/', {}, format='json',
        )
        assert r.status_code == 200
        demand.refresh_from_db()
        assert demand.need_status == PositionDemand.NeedStatus.PUBLISHED

    def test_待审核需求不能发布(self, auth_client, db):
        demand = _demand(need_status=PositionDemand.NeedStatus.PENDING)
        r = auth_client.post(
            f'{BASE}/position-demands/{demand.id}/publish/', {}, format='json',
        )
        assert r.status_code == 400
        assert '尚未通过审核' in str(r.data)

    def test_开放开关可切换(self, auth_client, db):
        demand = _demand(open_enabled=False)
        r = auth_client.post(
            f'{BASE}/position-demands/{demand.id}/open/',
            {'open_enabled': True},
            format='json',
        )
        assert r.status_code == 200
        demand.refresh_from_db()
        assert demand.open_enabled is True

    def test_发布范围按批次时必须填批次号(self, auth_client, db):
        r = auth_client.post(
            f'{BASE}/position-demands/',
            {
                'name': '缺批次的需求',
                'scope_type': PositionDemand.ScopeType.BATCH,
                'need_status': PositionDemand.NeedStatus.PENDING,
            },
            format='json',
        )
        assert r.status_code == 400
        assert 'scope_batch' in str(r.data)


class Test开放判定顺序:
    """判定顺序：审核状态 → 开放开关 → 发布范围 → 面向届数/班级 → 窗口期。"""

    def test_第一步审核状态(self, db):
        person = _person('C91000001', '甲')
        demand = _demand(need_status=PositionDemand.NeedStatus.PENDING)
        opened, reason = _position_open_state(demand, person)
        assert opened is False
        assert '审核' in reason

    def test_第二步开放开关(self, db):
        person = _person('C91000002', '乙')
        demand = _demand(open_enabled=False)
        opened, reason = _position_open_state(demand, person)
        assert opened is False
        assert '未开放报名' in reason

    def test_第三步发布范围按批次(self, db):
        person = _person('C91000003', '丙', batch='B2026')
        demand = _demand(
            scope_type=PositionDemand.ScopeType.BATCH, scope_batch='B2026',
        )
        assert _position_open_state(demand, person)[0] is True

        other = _person('C91000004', '丁', batch='B2025')
        opened, reason = _position_open_state(demand, other)
        assert opened is False
        assert 'B2026' in reason

    def test_第三步发布范围按意向部门(self, db):
        person = _person('C91000005', '戊', intent_bu='能电BG')
        demand = _demand(
            scope_type=PositionDemand.ScopeType.INTENT_DEPT,
            scope_intent_depts=['能电BG'],
        )
        assert _position_open_state(demand, person)[0] is True

        other = _person('C91000006', '己', intent_bu='醒电BG')
        opened, reason = _position_open_state(demand, other)
        assert opened is False
        assert '意向部门' in reason

    def test_第四步面向批次(self, db):
        person = _person('C91000007', '庚', batch='B2026')
        demand = _demand(open_batch_no='B2026')
        assert _position_open_state(demand, person)[0] is True

        other = _person('C91000008', '辛', batch='B2025')
        opened, reason = _position_open_state(demand, other)
        assert opened is False
        assert '面向' in reason

    def test_第五步窗口期(self, db):
        person = _person('C91000009', '壬')
        future = _demand(
            open_start=date(2099, 1, 1), open_end=date(2099, 12, 31),
        )
        opened, reason = _position_open_state(future, person)
        assert opened is False
        assert '开放报名' in reason

        past = _demand(open_start=date(2000, 1, 1), open_end=date(2000, 12, 31))
        opened, reason = _position_open_state(past, person)
        assert opened is False
        assert '截止报名' in reason

    def test_多条件不满足时按顺序取第一个原因(self, db):
        """审核状态排在最前：即使开放开关也关着，先报审核原因。"""
        person = _person('C91000010', '癸')
        demand = _demand(
            need_status=PositionDemand.NeedStatus.REJECTED,
            open_enabled=False,
            scope_type=PositionDemand.ScopeType.BATCH,
            scope_batch='B9999',
            open_start=date(2099, 1, 1),
        )
        opened, reason = _position_open_state(demand, person)
        assert opened is False
        assert '驳回' in reason
