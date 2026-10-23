"""批次规则引擎（契约 §4.2 / 逆向清单 §4.4，算法 A10 / A11）。

锁定四件事：
1. 编号生成：模板变量 `{YYYY}{YY}{MM}{M}{DD}{SEQ}{N}`、序号按 cycle 归零、位宽补零；
2. 匹配唯一性：`start_date ≤ 日期 ≤ end_date` 命中唯一规则，区间重叠 / 无命中 → 不归属；
3. `batch-rules/apply/`：**只补空值**，不覆盖人工填过的批次；
4. `batch-rules/recalc/`：**先返回变更预览（不落库）**，body `{"apply": true}` 才落库。
"""
from datetime import date

import pytest

from apps.campus_control.models import BatchNaming, BatchRule, Person
from apps.campus_control.views import (
    assign_batch_sequences,
    match_batch_rule,
    render_batch_no,
)

pytestmark = pytest.mark.django_db

BASE = '/api/v1/campus'


def _person(code, name, entry_date=None, batch=''):
    """建校招生档案。

    ⚠️ 不直接传入职日期：`Person.save()` 会按 `campus_rotation.rules.batch_no`
    自动回填批次（聂荣口径「批次基于入职时间自动生成」），会把「批次为空」这个
    待回填态吃掉 → 先建档案，再用 queryset update 单独补日期。
    """
    person = Person.objects.create(
        code=code, name=name, bu='能电BG', school='985', sex='男', major='工学',
        status='在职', batch=batch,
    )
    if entry_date is not None:
        Person.objects.filter(id=person.id).update(actual_entry_date=entry_date)
        person.refresh_from_db()
    return person


def _rule(code, name, start, end, sort=0, enabled=True):
    return BatchRule.objects.create(
        code=code, name=name, start_date=start, end_date=end, sort=sort, enabled=enabled,
    )


class Test编号生成:
    """算法 A11：批次号 = 命名模板 + 区间起始日 + 批次序号。"""

    def test_默认模板(self):
        assert render_batch_no('{YY}{MM}{SEQ}', date(2026, 7, 1), 1, 2) == '260701'

    def test_全部变量(self):
        got = render_batch_no(
            '{YYYY}{YY}{MM}{M}{DD}{SEQ}{N}', date(2026, 7, 1), 1, 2,
        )
        assert got == '2026260770101第1批'

    def test_序号按位宽补零(self):
        assert render_batch_no('{SEQ}', date(2026, 7, 1), 7, 3) == '007'
        assert render_batch_no('{SEQ}', date(2026, 7, 1), 7, 1) == '7'

    def test_N变量取整数序号(self):
        assert render_batch_no('{N}', date(2026, 7, 1), 12, 2) == '第12批'

    def test_日期取区间起始日(self):
        """日期部分来自区间起始日（逆向清单 A11 原文）。"""
        assert render_batch_no('{YYYY}-{MM}-{DD}', date(2026, 3, 9), 1, 2) == '2026-03-09'

    def test_无起始日不生成(self):
        assert render_batch_no('{YY}{MM}{SEQ}', None, 1, 2) == ''


class Test序号归零:
    """序号按 cycle 粒度归零（每月 / 每年 / 全局）。"""

    @pytest.fixture
    def rules(self, db):
        return [
            _rule('260701', '7 月批', date(2026, 7, 1), date(2026, 7, 31), sort=1),
            _rule('260801', '8 月批', date(2026, 8, 1), date(2026, 8, 31), sort=2),
        ]

    def test_每月归零(self, rules):
        seqs = assign_batch_sequences(rules, BatchNaming.Cycle.MONTH, 1)
        assert seqs[rules[0].id] == 1
        assert seqs[rules[1].id] == 1

    def test_每年归零(self, rules):
        seqs = assign_batch_sequences(rules, BatchNaming.Cycle.YEAR, 1)
        assert seqs[rules[0].id] == 1
        assert seqs[rules[1].id] == 2

    def test_全局递增(self, rules):
        seqs = assign_batch_sequences(rules, BatchNaming.Cycle.NONE, 1)
        assert seqs[rules[0].id] == 1
        assert seqs[rules[1].id] == 2

    def test_序号起始值可配(self, rules):
        seqs = assign_batch_sequences(rules, BatchNaming.Cycle.NONE, 3)
        assert seqs[rules[0].id] == 3
        assert seqs[rules[1].id] == 4


class Test区间匹配:
    """算法 A10：按日期区间命中规则，命中区间唯一。"""

    @pytest.fixture
    def rules(self, db):
        return [
            _rule('260701', '7 月批', date(2026, 7, 1), date(2026, 7, 31), sort=1),
            _rule('260801', '8 月批', date(2026, 8, 1), date(2026, 8, 31), sort=2),
        ]

    def test_命中唯一规则(self, rules):
        assert match_batch_rule(rules, date(2026, 7, 15)).code == '260701'
        assert match_batch_rule(rules, date(2026, 8, 1)).code == '260801'

    def test_区间端点含端点(self, rules):
        assert match_batch_rule(rules, date(2026, 7, 1)).code == '260701'
        assert match_batch_rule(rules, date(2026, 7, 31)).code == '260701'

    def test_无命中不归属(self, rules):
        assert match_batch_rule(rules, date(2026, 9, 1)) is None
        assert match_batch_rule(rules, None) is None

    def test_区间重叠不归属(self, db):
        """命中区间必须唯一：重叠时无法归属（避免同一人被两个批次号抢走）。"""
        rules = [
            _rule('A', '规则 A', date(2026, 7, 1), date(2026, 7, 31), sort=1),
            _rule('B', '规则 B', date(2026, 7, 15), date(2026, 8, 15), sort=2),
        ]
        assert match_batch_rule(rules, date(2026, 7, 20)) is None


class Test应用回写:
    """`batch-rules/apply/`：只补空值。"""

    def test_只补空值不覆盖人工批次(self, auth_client, db):
        _rule('260701', '7 月批', date(2026, 7, 1), date(2026, 7, 31))
        empty = _person('C93000001', '甲', entry_date=date(2026, 7, 10))
        manual = _person('C93000002', '乙', entry_date=date(2026, 7, 11), batch='人工批次')
        outside = _person('C93000003', '丙', entry_date=date(2026, 9, 10))

        r = auth_client.post(f'{BASE}/batch-rules/apply/', {}, format='json')
        assert r.status_code == 200
        data = r.data['data']
        assert data['filled'] == 1
        assert data['skipped'] == 1
        assert data['unmatched'] == 1

        empty.refresh_from_db()
        manual.refresh_from_db()
        outside.refresh_from_db()
        assert empty.batch == '260701'
        assert manual.batch == '人工批次'
        assert outside.batch == ''

    def test_已停用规则不参与回写(self, auth_client, db):
        _rule('260701', '7 月批', date(2026, 7, 1), date(2026, 7, 31), enabled=False)
        person = _person('C93000004', '丁', entry_date=date(2026, 7, 10))

        r = auth_client.post(f'{BASE}/batch-rules/apply/', {}, format='json')
        assert r.status_code == 200
        assert r.data['data']['filled'] == 0
        person.refresh_from_db()
        assert person.batch == ''


class Test重算预览:
    """`batch-rules/recalc/`：先预览不落库，`apply=true` 才落库。"""

    @pytest.fixture
    def seeded(self, db):
        rule = _rule('OLDBATCH', '7 月批', date(2026, 7, 1), date(2026, 7, 31))
        person = _person('C93000005', '戊', entry_date=date(2026, 7, 10), batch='OLDBATCH')
        BatchNaming.objects.create(
            template='{YY}{MM}{SEQ}', seq_width=2, seq_start=1,
            cycle=BatchNaming.Cycle.MONTH, date_field=BatchNaming.DateField.ENTRY,
        )
        return rule, person

    def test_预览不落库(self, auth_client, seeded):
        rule, person = seeded
        r = auth_client.post(f'{BASE}/batch-rules/recalc/', {}, format='json')
        assert r.status_code == 200
        data = r.data['data']
        assert data['applied'] is False
        assert data['changes'][0]['old'] == 'OLDBATCH'
        assert data['changes'][0]['new'] == '260701'
        assert data['person_changes'][0]['new'] == '260701'

        rule.refresh_from_db()
        person.refresh_from_db()
        assert rule.code == 'OLDBATCH'
        assert person.batch == 'OLDBATCH'

    def test_apply为真才落库(self, auth_client, seeded):
        rule, person = seeded
        r = auth_client.post(
            f'{BASE}/batch-rules/recalc/', {'apply': True}, format='json',
        )
        assert r.status_code == 200
        assert r.data['data']['applied'] is True

        rule.refresh_from_db()
        person.refresh_from_db()
        assert rule.code == '260701'
        assert person.batch == '260701'


class Test实时预览:
    """`batch-rules/preview/`：生成样例 + 命中统计。"""

    def test_预览返回样例与命中统计(self, auth_client, db):
        _rule('260701', '7 月批', date(2026, 7, 1), date(2026, 7, 31), sort=1)
        _rule('260801', '8 月批', date(2026, 8, 1), date(2026, 8, 31), sort=2)
        _person('C93000006', '己', entry_date=date(2026, 7, 10))
        _person('C93000007', '庚', entry_date=date(2026, 8, 10))
        _person('C93000008', '辛', entry_date=date(2026, 9, 10))  # 未命中
        _person('C93000009', '壬')                                  # 无日期、无批次

        r = auth_client.get(f'{BASE}/batch-rules/preview/')
        assert r.status_code == 200
        data = r.data['data']
        assert len(data['samples']) == 2
        assert data['samples'][0]['generated'] == '260701'
        assert data['samples'][1]['generated'] == '260801'
        assert data['samples'][0]['hit_count'] == 1
        assert data['samples'][1]['hit_count'] == 1
        assert data['hit_total'] == 2
        # 未命中 = 命中不到任何规则（含无日期人员）
        assert data['unmatched_count'] == 2
        assert data['no_date_count'] == 1
        # 无批次 = 当前批次字段为空的人数
        assert data['no_batch_count'] == 4

    def test_预览参数可临时覆盖模板(self, auth_client, db):
        _rule('260701', '7 月批', date(2026, 7, 1), date(2026, 7, 31))
        r = auth_client.get(
            f'{BASE}/batch-rules/preview/?template=%7BYYYY%7D%7BSEQ%7D&seq_width=3',
        )
        assert r.status_code == 200
        assert r.data['data']['samples'][0]['generated'] == '2026001'


class Test命名配置单例:
    """`batch-naming/`：GET 读、PUT 覆盖。"""

    def test_未配置时返回默认值(self, auth_client, db):
        r = auth_client.get(f'{BASE}/batch-naming/')
        assert r.status_code == 200
        data = r.data['data']
        assert data['template'] == '{YY}{MM}{SEQ}'
        assert data['seq_width'] == 2
        assert data['seq_start'] == 1
        assert data['cycle'] == 'month'
        assert data['date_field'] == 'entryDate'
        # GET 不产生副作用
        assert BatchNaming.objects.count() == 0

    def test_put覆盖后生效(self, auth_client, db):
        r = auth_client.put(
            f'{BASE}/batch-naming/',
            {'template': '{YYYY}{MM}{SEQ}', 'seq_width': 3, 'cycle': 'year'},
            format='json',
        )
        assert r.status_code == 200
        assert BatchNaming.objects.count() == 1

        r = auth_client.get(f'{BASE}/batch-naming/')
        assert r.data['data']['template'] == '{YYYY}{MM}{SEQ}'
        assert r.data['data']['seq_width'] == 3
        assert r.data['data']['cycle'] == 'year'

    def test_模板变量非法被拒(self, auth_client, db):
        r = auth_client.put(
            f'{BASE}/batch-naming/', {'template': '{XX}{MM}'}, format='json',
        )
        assert r.status_code == 400
        assert '命名模板' in str(r.data)

    def test_序号位数越界被拒(self, auth_client, db):
        r = auth_client.put(
            f'{BASE}/batch-naming/', {'seq_width': 9}, format='json',
        )
        assert r.status_code == 400
        assert '序号位数' in str(r.data)
