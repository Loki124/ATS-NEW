"""交易与结算（逆向清单 §4.4「交易和结算」）。

三个页签：收入统计（台账）/ 结算账单 / 定价管理。

锁定：
- 定价分档（排名分档 → 结算单价 / 底价）的解析口径；
- 台账金额兜底口径（出勤天数 × 单价）；
- 账单生成（账单号自动生成 + 结算人数 / 金额按台账汇总）；
- 收入统计与定价管理的聚合口径。
"""
from decimal import Decimal

import pytest

from apps.campus_control.models import Person
from apps.campus_placement.models import (
    Bill,
    PriceScheme,
    RevenueRecord,
    resolve_tier_price,
)

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus-placement'

TIERS = [
    {'rank': '1-10', 'price': 1200, 'floor': 1000},
    {'rank': '11-30', 'price': 900, 'floor': 700},
]


def _person(code, name):
    return Person.objects.create(
        code=code, name=name, bu='能电BG', school='985', sex='男', major='工学',
        status='在职', batch='B2026',
    )


class Test定价分档:
    """排名分档 → 结算单价 / 底价。"""

    @pytest.mark.parametrize(
        'rank,price,floor',
        [
            (1, Decimal('1200'), Decimal('1000')),
            (10, Decimal('1200'), Decimal('1000')),
            (11, Decimal('900'), Decimal('700')),
            (30, Decimal('900'), Decimal('700')),
        ],
    )
    def test_命中分档(self, rank, price, floor):
        assert resolve_tier_price(TIERS, rank) == (price, floor)

    def test_未命中分档返回空(self):
        assert resolve_tier_price(TIERS, 99) == (None, None)
        assert resolve_tier_price(TIERS, None) == (None, None)

    def test_分档缺rank被拒(self, auth_client, db):
        r = auth_client.post(
            f'{BASE}/price-schemes/',
            {'name': '坏分档', 'type': 'FIXED', 'tiers': [{'price': 100}]},
            format='json',
        )
        assert r.status_code == 400
        assert '缺少排名区间' in str(r.data)

    def test_方案与默认方案(self, auth_client, db):
        r = auth_client.post(
            f'{BASE}/price-schemes/',
            {
                'name': '2026 秋招定价', 'type': 'FIXED', 'batch': 'B2026',
                'tiers': TIERS, 'is_default': True, 'enabled': True,
            },
            format='json',
        )
        assert r.status_code == 201
        assert PriceScheme.objects.count() == 1

        r = auth_client.get(f'{BASE}/settlement/price/')
        assert r.status_code == 200
        data = r.data['data']
        assert len(data['schemes']) == 1
        assert data['default']['name'] == '2026 秋招定价'
        assert data['default']['tiers'][0]['rank'] == '1-10'

    def test_出价记录(self, auth_client, db):
        scheme = PriceScheme.objects.create(name='竞价方案', type='BID', tiers=TIERS)
        person = _person('C92000001', '甲')
        r = auth_client.post(
            f'{BASE}/price-bids/',
            {'scheme': scheme.id, 'person_id': person.id, 'price': '1150.00'},
            format='json',
        )
        assert r.status_code == 201


class Test台账金额:
    """输出台账：金额兜底 = 出勤天数 × 单价。"""

    def test_金额按出勤乘单价兜底(self, auth_client, db):
        person = _person('C92000002', '乙')
        r = auth_client.post(
            f'{BASE}/revenue-records/',
            {
                'person_id': person.id, 'ym': '2026-07', 'output_dept': '能电BG',
                'stage': '轮岗', 'attend_days': 22, 'unit_price': '1200.00',
            },
            format='json',
        )
        assert r.status_code == 201
        rec = RevenueRecord.objects.get(pk=r.data['data']['id'])
        assert rec.amount == Decimal('26400.00')

    def test_显式金额优先(self, auth_client, db):
        person = _person('C92000003', '丙')
        auth_client.post(
            f'{BASE}/revenue-records/',
            {
                'person_id': person.id, 'ym': '2026-07', 'output_dept': '能电BG',
                'attend_days': 22, 'unit_price': '1200.00', 'amount': '25000.00',
            },
            format='json',
        )
        rec = RevenueRecord.objects.get()
        assert rec.amount == Decimal('25000.00')


class Test账单生成:
    """结算账单：账单号自动生成 + 结算人数 / 金额按台账汇总。"""

    def test_账单按台账汇总生成(self, auth_client, db):
        p1 = _person('C92000004', '丁')
        p2 = _person('C92000005', '戊')
        RevenueRecord.objects.create(
            person=p1, ym='2026-07', output_dept='能电BG', attend_days=22,
            unit_price=Decimal('1200.00'), amount=Decimal('26400.00'),
        )
        RevenueRecord.objects.create(
            person=p2, ym='2026-07', output_dept='能电BG', attend_days=20,
            unit_price=Decimal('900.00'), amount=Decimal('18000.00'),
        )

        r = auth_client.post(
            f'{BASE}/bills/',
            {'business_dept': '能电BG', 'period': '2026-07'},
            format='json',
        )
        assert r.status_code == 201
        bill = Bill.objects.get()
        assert bill.bill_no.startswith('B202607')
        assert bill.person_count == 2
        assert bill.amount == Decimal('44400.00')
        assert bill.status == Bill.Status.PENDING

    def test_账单可确认(self, auth_client, db):
        bill = Bill.objects.create(bill_no='B202607001', period='2026-07')
        r = auth_client.patch(
            f'{BASE}/bills/{bill.id}/',
            {'status': Bill.Status.CONFIRMED},
            format='json',
        )
        assert r.status_code == 200
        bill.refresh_from_db()
        assert bill.status == Bill.Status.CONFIRMED


class Test收入统计:
    """`settlement/stat/` 聚合口径。"""

    def test_按月份部门阶段聚合(self, auth_client, db):
        p1 = _person('C92000006', '己')
        p2 = _person('C92000007', '庚')
        RevenueRecord.objects.create(
            person=p1, ym='2026-07', output_dept='能电BG', stage='轮岗',
            attend_days=22, unit_price=Decimal('1200.00'), amount=Decimal('26400.00'),
        )
        RevenueRecord.objects.create(
            person=p2, ym='2026-07', output_dept='能电BG', stage='定岗',
            attend_days=20, unit_price=Decimal('900.00'), amount=Decimal('18000.00'),
        )
        RevenueRecord.objects.create(
            person=p1, ym='2026-08', output_dept='能电BG', stage='轮岗',
            attend_days=23, unit_price=Decimal('1200.00'), amount=Decimal('27600.00'),
        )

        r = auth_client.get(f'{BASE}/settlement/stat/?ym=2026-07&output_dept=能电BG')
        assert r.status_code == 200
        data = r.data['data']
        assert len(data['rows']) == 2
        assert data['total_amount'] == 44400.0
        assert data['total_attend_days'] == 42
        assert {row['stage'] for row in data['rows']} == {'轮岗', '定岗'}
